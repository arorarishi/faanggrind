# TLS certificate expired in production — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/tls-certificate-expired

[DevOps problems](/devops#problems)

OPSTroubleshooting#27Easy

# TLS certificate expired in production

tlscert-managerlets-encryptcertificatestroubleshootingkubernetesReported at Infosys, Wipro, Capgemini

## Problem statement

It is 00:03. The uptime monitor pages: `https://shop.example.com` fails with `x509: certificate has expired or is not yet valid`, and a customer screenshot shows the browser's "Your connection is not private" page. The site runs on EKS behind ingress-nginx (still common, though the project was retired upstream in early 2026); cert-manager issues its certificates from Let's Encrypt with a DNS-01 solver on Route 53. Nothing was deployed today. Confirm what expired, find out why automatic renewal did not happen, get a valid certificate served within 20 minutes, and make sure the next failed renewal pages 14 days before it matters.

## Requirements

### Functional

* Confirm from the server, not the browser, which certificate is served and when it expired.
* Say where the certificate lives and which renewal mechanism owns it, and read that mechanism's own status.
* Walk cert-manager's chain: Certificate, CertificateRequest, Order, Challenge, and the ClusterIssuer, and name the step that is failing.
* Rule out the look-alikes: a missing intermediate chain, clock skew on the client, a stale certificate on one replica or one load balancer.
* Restore a valid certificate through the proper path (fix the cause and let cert-manager issue), and verify from outside.
* Add expiry monitoring that alerts at 14 days and on any cert-manager Certificate that is not Ready.

### Non-functional

* Time from page to a valid certificate under 20 minutes; Let's Encrypt issuance itself takes 1 to 3 minutes once the challenge passes.
* Blast radius: 100 percent of browser users on `shop.example.com` get a hard error (no bypass for HSTS sites), about 1,200 sessions per hour at midnight.
* The fix is in Terraform (the IAM role) and Git, not a hand-edited role that the next apply removes.
* Alert at 14 days before expiry on every public endpoint, and within 15 minutes on any Certificate with `Ready=False`.

## Back-of-the-envelope estimates

**Impact.** Let's Encrypt certificates are valid for 90 days and cert-manager renews at two thirds of the lifetime, so renewal attempts started 30 days before expiry. The Certificate has been `Ready=False` for 30 days with the attempt counter at 26: cert-manager's retry delay doubles per failed attempt from 1 hour up to a cap of 32 hours, so the first 6 attempts take about 63 hours and the next 20 take 32 hours each, about 30 days in all. With HSTS, no user can click through, so every request fails: at 1,200 sessions an hour that is 20 lost sessions per minute, 400 in the 20-minute target. The 14-day alert would have given 14 days of warning; the `Ready=False` alert would have given 30 days.

## API

```
# 1. Confirm from the server: which certificate does it serve, and until when? Use SNI (-servername) or you get the default cert.
openssl s_client -connect shop.example.com:443 -servername shop.example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
# subject=CN = shop.example.com
# issuer=C = US, O = Let's Encrypt, CN = R11
# notBefore=Aug  5 00:01:12 2026 GMT
# notAfter=Nov  3 00:01:12 2026 GMT          <- expired 2 minutes ago

# 2. The same from curl, with the handshake detail. -k would bypass; do not use it except to see the headers.
curl -vI https://shop.example.com 2>&1 | grep -E "expire|SSL certificate|subject|issuer"
# * SSL certificate problem: certificate has expired

# 3. Rule out the look-alikes: full chain as sent, and your own clock.
openssl s_client -connect shop.example.com:443 -servername shop.example.com -showcerts </dev/null 2>/dev/null \
  | grep -c "BEGIN CERTIFICATE"       # 2 = leaf plus intermediate; 1 = chain missing (a different error: unable to get local issuer)
date -u; timedatectl status | grep -i "synchronized"

# 4. Where does it live? Here: a Kubernetes Secret owned by cert-manager, referenced by the Ingress.
kubectl get ingress -n shop shop-web -o jsonpath='{.spec.tls}{"\n"}'
# [{"hosts":["shop.example.com"],"secretName":"shop-example-com-tls"}]
kubectl get certificate -n shop
# NAME               READY   SECRET                 AGE
# shop-example-com   False   shop-example-com-tls   240d

# 5. Walk the cert-manager chain. Each describe names the next object.
kubectl describe certificate -n shop shop-example-com | sed -n '/Status:/,$p'
#   Conditions:  Ready False  Reason: Expired   Message: Certificate expired on Tue, 03 Nov 2026 00:01:12 UTC
#                Issuing True Reason: ...
#   Failed Issuance Attempts: 26     Last Failure Time: 2026-11-01T12:10:44Z     Not After: 2026-11-03T00:01:12Z
kubectl get certificaterequest -n shop
kubectl describe certificaterequest -n shop shop-example-com-1 | grep -A3 "Conditions"
kubectl get order -n shop
# NAME                          STATE     AGE
# shop-example-com-1-146226287  pending   4h
kubectl get challenge -n shop
# NAME                                   STATE     DOMAIN             REASON                                                        AGE
# shop-example-com-1-146226287-56134098  pending   shop.example.com   presenting failed: ... AccessDenied: User: arn:aws:sts::123456789012:assumed-role/cert-manager-dns01/... is not authorized to perform: route53:ChangeResourceRecordSets on resource: arn:aws:route53:::hostedzone/Z0123456789ABC   4h
kubectl describe challenge -n shop shop-example-com-1-146226287-56134098 | sed -n '/Status:/,$p'

# 6. The issuer and the identity behind it.
kubectl describe clusterissuer letsencrypt-prod | grep -A12 "Solvers"
kubectl get sa -n cert-manager cert-manager -o jsonpath='{.metadata.annotations}{"\n"}'
# {"eks.amazonaws.com/role-arn":"arn:aws:iam::123456789012:role/cert-manager-dns01"}
aws iam get-role --role-name cert-manager-dns01
aws iam list-attached-role-policies --role-name cert-manager-dns01     # empty: the policy attachment is gone
cd infra && git log --since="40 days ago" --oneline -- modules/cert-manager-iam/

# 7. After the IAM fix: trigger a retry now instead of waiting for the back-off (up to 32 h).
cmctl renew -n shop shop-example-com        # or delete the pending Order; cert-manager creates a new one
kubectl get challenge -n shop -w            # pending -> valid in 1 to 3 minutes
kubectl get certificate -n shop             # READY True

# 8. Verify from outside, then from every replica of the ingress.
openssl s_client -connect shop.example.com:443 -servername shop.example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -enddate -checkend 1209600     # exits 0 if valid for 14 more days
```

## Data model

```
What the server sends (openssl x509)
  subject, issuer        whose certificate, which CA
  notBefore, notAfter    validity window; expired = now > notAfter
  chain count            2 for Let's Encrypt (leaf + intermediate); 1 means the chain is missing: "unable to get local issuer certificate", not "expired"
  client clock           a client years off sees "not yet valid" or "expired" for a valid certificate

Where certificates live, who renews them, how each fails
  ALB + ACM           ACM renews DNS-validated certs while the validation CNAME exists and the cert is in use;
                      CNAME deleted -> renewal stops, AWS Health events at 30, 15, 7, 3 and 1 days
  Nginx on a VM       certbot renew from a systemd timer or cron; fails if the timer is missing, port 80 is closed,
                      or /.well-known/acme-challenge/ is redirected to HTTPS before the challenge is served
  Kubernetes          cert-manager Certificate -> CertificateRequest -> Order -> Challenge; fails if the ClusterIssuer's
                      credentials changed, the DNS-01 role lost permission, or the HTTP-01 ingress path is blocked

cert-manager fields that decide it
  Certificate.status.conditions[Ready]         False, Reason Expired | DoesNotExist | ...
  Certificate.status.conditions[Issuing]       True while an issuance is in progress
  Certificate.status.notAfter                  expiry of what is in the Secret
  Certificate.status.renewalTime               when renewal is attempted (default: 2/3 of duration, so day 60 of 90)
  Certificate.status.failedIssuanceAttempts    26; retry after 1h x 2^(attempts-1), capped at 32 h
  Certificate.status.lastFailureTime
  CertificateRequest.status.conditions         Ready False while the Order is pending
  Order.status.state                           pending | valid | errored | invalid
  Challenge.status.state, .reason              pending, "presenting failed: ... AccessDenied ... route53:ChangeResourceRecordSets"
  Challenge.status.presented                   false: the TXT record was never written
  ClusterIssuer.spec.acme.solvers[].dns01.route53   region, hostedZoneID, role or ambient credentials
  cert-manager ServiceAccount annotation       eks.amazonaws.com/role-arn (IRSA) or an EKS Pod Identity association

IAM the DNS-01 solver needs (Route 53)
  route53:GetChange on arn:aws:route53:::change/*
  route53:ChangeResourceRecordSets and route53:ListResourceRecordSets on the hosted zone (TXT only)
  route53:ListHostedZonesByName on *   (optional when hostedZoneID is set)

Monitoring
  probe_ssl_earliest_cert_expiry - time() < 14*24*3600      blackbox exporter, per public endpoint
  certmanager_certificate_ready_status{condition="False"} == 1 for 15m
  certmanager_certificate_expiration_timestamp_seconds - time() < 14*24*3600
```

## Diagnosis and fix

1. **Confirm and scope.** `openssl s_client` with `-servername` shows the served leaf expired at 00:01 UTC; the chain has 2 certificates and your clock is synchronised, so this is a real expiry, not a chain or clock look-alike. Say so in the channel with the ETA.
2. **Find the owner.** The Ingress references Secret `shop-example-com-tls`; `kubectl get certificate -n shop` shows the cert-manager Certificate that owns it with `READY False`. So renewal is cert-manager's job and it has been failing. Not ACM, not certbot: the load balancer in front is a TCP passthrough.
3. **Walk the chain.** The Certificate's conditions say `Ready False, Reason Expired` and `Issuing True`, with `failedIssuanceAttempts: 26` and a last failure 36 hours ago; the 32-hour back-off then created the current Order 4 hours ago. The CertificateRequest is not Ready, the Order is `pending`, and the Challenge's reason is the answer: `presenting failed: ... AccessDenied ... not authorized to perform: route53:ChangeResourceRecordSets`. The solver cannot write the `_acme-challenge` TXT record, so the Order never completes.
4. **Find why.** The ClusterIssuer uses ambient credentials through IRSA: the cert-manager ServiceAccount carries the role annotation, the role exists, but `list-attached-role-policies` is empty. `git log` on the IAM module shows a "cleanup unused policies" commit 31 days ago that removed the Route 53 policy attachment because nothing in the application repos referenced it. Root cause: a Terraform cleanup removed the DNS-01 role's Route 53 permissions, and renewal has failed 26 times since day 60.
5. **Fix through the proper path.** Revert the commit (the attachment plus the policy with `route53:GetChange`, `ChangeResourceRecordSets`, `ListResourceRecordSets` on the zone, and `ListHostedZonesByName`), plan, apply: about 3 minutes. No pod restart is needed for IRSA, the next STS call gets the new permissions.
6. **Retry now.** cert-manager's back-off would wait up to 32 hours. `cmctl renew -n shop shop-example-com` (or deleting the pending Order) starts a fresh Order. Watch the Challenge go `pending` to `valid`, then the Certificate turns `Ready True` and the Secret is updated; ingress-nginx reloads it within seconds.
7. **Verify.** `openssl x509 -checkend 1209600` exits 0 from outside; `curl -vI` shows the new `notAfter` about 90 days out; the uptime monitor clears; check each ingress replica with `-connect <pod ip>` to be sure none serves a cached old cert.
8. **Prevent.** A blackbox exporter probe per public hostname with an alert at 14 days; cert-manager's own metrics with an alert on any Certificate `Ready=False` for 15 minutes; an IAM role tagged as owned by cert-manager with a Terraform policy test that fails a plan removing it.

## Architecture diagram

Rendering diagram…

## Deep dives

### Read the server, not the browser

A browser error says only that the chain did not verify. `openssl s_client -servername` with `openssl x509 -dates` gives the exact leaf and its `notAfter`; without `-servername` a multi-host endpoint returns its default certificate and you debug the wrong one. Two look-alikes produce the same browser page: a server that sends only the leaf without the intermediate gives `unable to get local issuer certificate` and a chain count of 1, fixed by serving `fullchain.pem`; and a client whose clock is far off sees a perfectly valid certificate as expired or not yet valid, visible when `date -u` disagrees with the `notBefore` and `notAfter` window.

### Three homes, three renewal mechanisms, three ways to fail silently

On an ALB, ACM renews a DNS-validated certificate while the validation CNAME exists and the certificate is in use; delete the CNAME during a DNS tidy-up and renewal stops, with warnings only in AWS Health and EventBridge. On a VM, certbot renews from a systemd timer or cron; a rebuilt host without the timer, a firewall that closed port 80, or an Nginx redirect that sends `/.well-known/acme-challenge/` to HTTPS before the challenge is served all break HTTP-01 quietly, and `certbot renew --dry-run` shows which. On Kubernetes, cert-manager turns a Certificate into a CertificateRequest, then an Order, then one Challenge per domain; the error lives on the deepest object, which is why the walk goes Certificate, CertificateRequest, Order, Challenge, and the ClusterIssuer last.

### Why the retry waits and how to skip it

cert-manager records `failedIssuanceAttempts` and waits `1 hour x 2^(attempts-1)` before the next try, which after 6 failures is already over a day and is capped in practice at 32 hours. That is correct behaviour against a rate-limited CA, and it is why a fixed permission does not fix the site immediately. `cmctl renew` sets the Issuing condition and starts a new Order at once; deleting the stuck Order has the same effect. Let's Encrypt then validates the TXT record and issues in 1 to 3 minutes. Let's Encrypt certificates are valid for 90 days, with an opt-in 6-day short-lived option, and the recommended renewal cadence is every 60 days, which is exactly where cert-manager's default two-thirds point lands.

### Automation plus monitoring, not calendar reminders

A calendar reminder on day 85 depends on a person reading it and remembering how issuance works. The renewal here had been failing for 30 days in plain sight on the Certificate object. Two cheap alerts cover every home: a blackbox exporter HTTPS probe per public hostname with `probe_ssl_earliest_cert_expiry - time() < 14 days`, which catches ALB, VM and cluster alike from the outside; and cert-manager's `certmanager_certificate_ready_status` for the inside. The third guard is on the cause: IAM that automation depends on is tagged and tested in Terraform so a cleanup cannot remove it without a failing plan.

## Evaluation

**Did you find it?** One sentence: "the Certificate has been `Ready=False` for 30 days because a Terraform cleanup removed the Route 53 policy from the cert-manager DNS-01 role, so every Challenge fails with `AccessDenied` on `route53:ChangeResourceRecordSets` and the Order never completes." Evidence: the served leaf's `notAfter`, the Certificate conditions and `failedIssuanceAttempts`, the pending Order, the Challenge reason, the empty policy list on the role, and the git commit.

**Is it fixed?** The Challenge goes `valid`, the Certificate shows `Ready True` with `notAfter` about 90 days out, `openssl x509 -checkend 1209600` exits 0 from outside against every ingress replica, and the uptime monitor is green.

**Is it prevented?** The blackbox expiry alert at 14 days on every public hostname; the cert-manager `Ready=False` alert at 15 minutes; the IAM policy restored in Terraform with a test that fails a plan removing it; the ClusterIssuer and its role documented together so the dependency is visible.

**What a strong answer adds.** `-servername` and why it matters; the chain-count and clock-skew look-alikes; the four-object walk and that the error is on the deepest one; the exponential back-off and `cmctl renew`; the 90-day validity and 60-day renewal numbers; and the ACM and certbot failure modes for the same symptom in other homes.

**What a weak answer does.** Pastes a new certificate by hand into the Secret (cert-manager overwrites it, or it expires again in 90 days), restarts the ingress, or adds `-k` to the health check so the monitor goes green.

## Bottlenecks & mitigations

* The back-off: after many failures cert-manager waits up to 32 hours, so the fix must be followed by a manual renew.
* Let's Encrypt rate limits: repeated failed Orders count against the account; do not loop a delete-and-retry.
* DNS propagation for DNS-01: the self-check waits for the TXT record to be visible, usually 1 to 2 minutes on Route 53.
* Terraform apply time and approval: the IAM revert needs a reviewer at midnight; a documented break-glass applier avoids waiting.

## Failure modes

* **Debugging the browser instead of the server.** The browser cannot tell expiry from a missing chain or a bad clock. Mitigation: `openssl s_client` with `-servername` first.
* **Fixing the Secret by hand.** cert-manager reconciles it back or the hand-made one expires unseen. Mitigation: fix the issuer's cause and let it issue.
* **Fixing the cause and waiting.** The back-off is up to 32 hours. Mitigation: `cmctl renew` or delete the pending Order.
* **IAM "cleanups" that remove what automation uses.** Nothing in app repos references the DNS-01 role. Mitigation: tag and test the role in Terraform; a plan that removes it fails.
* **Redirecting all HTTP to HTTPS on a certbot host.** HTTP-01 never completes. Mitigation: exempt `/.well-known/acme-challenge/` from the redirect; run `certbot renew --dry-run` after Nginx changes.
* **Deleting the ACM validation CNAME.** Renewal stops silently. Mitigation: the CNAME is managed in the same Terraform as the certificate.
* **Monitoring only the cluster.** The ALB certificate expires unseen. Mitigation: external blackbox probes on every public hostname.
* **Alert at 100 percent, in other words at expiry.** Zero days of warning. Mitigation: 14 days before, and on `Ready=False`.

## Follow-up questions interviewers ask

* The Challenge says `Waiting for dns-01 challenge propagation` for 20 minutes. What do you check, inside and outside the cluster?
* The site is on an ALB with ACM and the certificate shows `PENDING_VALIDATION` during renewal. What happened and what is the fix?
* The same symptom on a VM with certbot and an Nginx `return 301 https://` on port 80. Show the Nginx fix.
* Users on one office network see the error and nobody else does. What is different there?
* Let's Encrypt offers 6-day certificates. What changes in your renewal and monitoring design if you adopt them?
* Write the two Prometheus alert rules: expiry within 14 days from the blackbox exporter, and a cert-manager Certificate not Ready for 15 minutes.

## Lessons that cover this

* [#4Networking for DevOps - TCP/IP, DNS, HTTP, TLS, SSHFoundations](/devops/learn/networking-for-devops)
* [#7Web servers, reverse proxies and TLS - Nginx, certificates, process managersBuild and ship](/devops/learn/nginx-reverse-proxy-tls)
* [#21SRE practice - SLOs, error budgets, incidents and postmortemsOperate](/devops/learn/sre-slos-incidents-postmortems)

## Further reading

* [cert-manager documentationGuidecert-manager.io](https://cert-manager.io/docs/)
* [Let's Encrypt: how it worksGuideletsencrypt.org](https://letsencrypt.org/how-it-works/)
* [Kubernetes documentation: ConceptsGuidekubernetes.io](https://kubernetes.io/docs/concepts/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousDeploy rolled out, users see errors, readiness probes flapping](/devops/problems/bad-deploy-readiness-probes)[NextCI pipeline became slow and flaky](/devops/problems/slow-flaky-ci-pipeline)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [Diagnosis and fix](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
