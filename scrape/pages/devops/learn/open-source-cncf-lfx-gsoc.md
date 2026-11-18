# Open source - contributing to CNCF projects, LFX and GSoC — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/open-source-cncf-lfx-gsoc

[DevOps roadmap](/devops)

ContributeLesson #26StudyIntermediate 5 h

# Open source - contributing to CNCF projects, LFX and GSoC

Open source contribution is proof of skill that no certificate matches: a merged pull request in Kubernetes, Helm or Prometheus shows you can read a large Go codebase, follow a review process and work with strangers. This lesson explains how CNCF projects are organised, how to pick one and climb its contribution ladder, how LFX Mentorship and GSoC work, and gives a 12-week plan from zero to a first merged PR.

open sourcecncfkuberneteslfx mentorshipgsocgocareer

## Why it matters

A DevOps or platform engineer spends the day inside tools other people wrote: Kubernetes, Argo CD, Prometheus, Terraform providers. Someone who has fixed a bug in one of them debugs it faster and is trusted sooner. Recruiters at product companies open the GitHub link on a resume; a merged PR with a review thread is a work sample that a project on a personal account is not. LFX Mentorship and GSoC turn that first PR into three months of paid, mentored work on a real project, and both select mostly on contributions you have already made. Interviewers ask "tell me about a contribution" because the answer reveals how you learn.

Read first: [Git and trunk-based workflows](/devops/learn/git-and-trunk-based-workflows), [Python and Go for automation and tooling](/devops/learn/python-and-go-for-devops), [Kubernetes architecture and core objects](/devops/learn/kubernetes-architecture-core-objects), [Kubernetes internals and operators in Go](/devops/learn/kubernetes-internals-operators-go)

## Lesson

### Why contribution is the strongest signal

A hiring manager cannot run your college project and cannot see your work at a previous employer. They can open a pull request on github.com/kubernetes/kubernetes and read every comment a maintainer left you, how you answered, how many rounds it took, and whether your tests pass. That thread shows four things at once: you can read a codebase you did not write, you can follow a strict process, you take review well, and you finish. No interview question tests all four.

The goal of this lesson is one merged PR in a CNCF project, then a mentorship. Both are reachable for a second-year student in one semester if you follow the order below.

### The CNCF projects to know, by category

The Cloud Native Computing Foundation (CNCF) hosts projects under the Linux Foundation. Projects move through three maturity levels: sandbox, incubating and graduated. Graduated projects have proven governance, security review and adoption; these are the ones interviewers name. The list below was checked on the CNCF projects page; the categories follow the CNCF project listing.

| Category | Graduated projects you should recognise | What they do |
| --- | --- | --- |
| Orchestration and runtime | Kubernetes, containerd, CRI-O, etcd, KubeEdge, Karmada | Scheduling, running containers, the cluster store, edge and multi-cluster |
| Packaging and delivery, GitOps | Helm, Argo, Flux | Charts, application delivery from Git |
| Observability | Prometheus, OpenTelemetry, Jaeger, Fluentd | Metrics, traces, logs, the collector standard |
| Networking and service mesh | Cilium, Envoy, CoreDNS, Istio, Linkerd | eBPF networking, the proxy under most meshes, cluster DNS, meshes |
| Security and policy | cert-manager, Kyverno, Open Policy Agent, Falco, SPIFFE and SPIRE, in-toto, The Update Framework, Harbor | Certificates, admission policy, runtime detection, workload identity, supply chain, registry |
| Autoscaling and serverless | KEDA, Knative, Dapr, CloudEvents | Event-driven scaling, serverless on Kubernetes, application runtime |
| Storage and data | Rook, Vitess, TiKV, CubeFS | Storage orchestration, sharded MySQL, key-value, distributed file system |
| Platform and infrastructure | Crossplane, Buildpacks, Dragonfly | Cloud resources as Kubernetes objects, images without Dockerfiles, image distribution |

Backstage, KServe, Thanos, Cortex, Tekton, Litmus and Chaos Mesh are incubating projects you will also meet. For a first contribution, prefer a graduated or incubating project with a `good first issue` label that has been used in the last month.

### How a CNCF project is run

Every project has a governance document naming who decides what. **Maintainers** own the project and are listed in a `MAINTAINERS` or `OWNERS` file. Kubernetes is big enough to split work into **Special Interest Groups (SIGs)**, each owning part of the code and holding a public meeting with recorded minutes. The current list on the kubernetes/community page has 24 SIGs; the ones you will meet first are Node, Network, Apps, CLI, Testing, Release, Docs, Scheduling, Storage, Auth, Autoscaling, API Machinery, Cluster Lifecycle and Contributor Experience. **Working Groups** are shorter-lived and span SIGs: Batch, Device Management, Node Lifecycle and others.

Large changes start as a **Kubernetes Enhancement Proposal (KEP)** in the kubernetes/enhancements repository: a design document that a SIG must accept before code is written, tracked through alpha, beta and GA across releases. Kubernetes releases about three times a year, and each release has an enhancement freeze and a code freeze that decide which KEPs land.

Before your first PR, every project asks for one of two legal steps. Kubernetes requires a signed **Contributor License Agreement (CLA)** through the Linux Foundation's EasyCLA; a bot blocks the PR with the `cncf-cla: no` label until it is signed. Many other projects use the **Developer Certificate of Origin (DCO)** instead: you add `Signed-off-by: Your Name <you@example.com>` to each commit with `git commit -s`. Check `CONTRIBUTING.md` to see which one applies.

Issues are sorted with labels. New issues get `needs-triage`; a SIG member runs `/triage accepted` after confirming it. `help wanted` marks issues the project wants outside help with; `good first issue` is a subset for new contributors, with the context already written up. `kind/bug`, `kind/feature`, `sig/node` and `area/kubectl` route the issue to the right people.

Kubernetes CI is **Prow**, a Kubernetes-based CI system that also runs the GitHub bot. You talk to it in comments:

```
# comment these on a pull request; the bot (k8s-ci-robot) acts on them
/retest              # rerun failed jobs (only after you have checked they are flakes, not your bug)
/assign @reviewer    # ask a specific OWNERS-file reviewer to look
/sig node            # route the PR to a SIG
/hold                # block merge until you comment /hold cancel
/lgtm                # a reviewer says "looks good to me"; adds the lgtm label
/approve             # an approver from the OWNERS file accepts it; adds approved
# lgtm + approved + green tests = the merge bot (tide) merges it, no human clicks merge
```

PRs from people outside the org wait for a member to comment `/ok-to-test` before CI runs at all.

### How to pick a project

Pick with your hands, not with a list. The order that works:

1. Use it for real. Install the project on kind or minikube and make it do its main job: deploy an app with Argo CD, scrape a target with Prometheus, issue a certificate with cert-manager.
2. Read the docs and the `CONTRIBUTING.md`, `docs/dev` or `DEVELOPMENT.md` file. Build it from source: `make build` and `make test`. If the build fails on your laptop, that is your first contribution: a docs fix.
3. Run it under a debugger or with verbose logs once, so you know the main loop.
4. Read issues for a week. Subscribe to the repository, skim every new issue, try to reproduce two. You will learn the vocabulary, the hot areas and which maintainers answer.
5. Join the project's Slack channel (CNCF and Kubernetes have public Slack workspaces) and attend one SIG or community meeting on video. Say nothing the first time.

Smaller projects (KEDA, Kyverno, cert-manager, Flux, Litmus, Backstage plugins) answer faster and have shorter queues than kubernetes/kubernetes itself. A first PR in Kubernetes core can wait weeks for review; a first PR in KEDA often merges in days.

### The contribution ladder

The ladder below is the same in every project; the Kubernetes membership names are in brackets and come from the community-membership document.

| Step | What you do | What it proves |
| --- | --- | --- |
| 1. Docs and typos | Fix a wrong flag in the docs, a broken link, a missing example | You can fork, branch, sign, open a PR and respond |
| 2. Tests | Add a unit test for an untested branch; make a flaky test deterministic | You can read the code well enough to test it |
| 3. Triage | Reproduce bug reports, ask for missing information, confirm or close | You understand user problems |
| 4. Small bug fixes | A `good first issue`: one function, one test | You can change a large Go codebase safely |
| 5. Features | Propose in an issue or KEP, get agreement, implement in small PRs | You can design in public |
| 6. Reviews | Review other people's PRs; comment on correctness, not style | Others start to trust your judgement |
| 7. Membership (member) | Sponsored by 2 reviewers; multiple merged contributions; 2FA on; subscribed to dev list | You are part of the org; CI runs on your PRs without ok-to-test |
| 8. Reviewer | Member for 3 months, primary reviewer for 5 PRs, reviewed or merged 20 substantial PRs; added to an OWNERS file | Your `/lgtm` counts |
| 9. Approver | Reviewer for 3 months, primary reviewer for 10, reviewed or merged 30 PRs; nominated by a subproject owner | Your `/approve` merges code |

Nobody skips the first four steps, and mentorship programmes select on them.

![Six ladder steps from using a project to reviewing and owning code, with GSoC and LFX Mentorship marked as entry points that expect the first four steps, and a side panel on what each step proves](/devops/img/cncf-contribution-ladder.svg)Six ladder steps from using a project to reviewing and owning code, with GSoC and LFX Mentorship marked as entry points that expect the first four steps, and a side panel on what each step proves

### Writing a good issue and a good PR

A good bug report has a title that states the symptom, the version (`kubectl version`, the project's `--version`), exact steps that reproduce it on a fresh kind cluster, what you expected, what happened with the real output pasted, and what you already tried. If you cannot reproduce it, say so and give what you have.

A good PR is small. The Kubernetes guide says it would rather have 100 small, obvious pull requests than 10 unreviewable monoliths. One PR fixes one thing and includes the test that failed before the fix. The description says what changed and why, links the issue with `Fixes #1234`, and fills the release note block if users will notice. Then the part most newcomers get wrong: responding to review. Answer every comment, even with "done". Push fix-up commits while the review is in progress so the reviewer can see the deltas; squash at the end when the project asks for it (Kubernetes lets you add the `tide/merge-method-squash` label instead of squashing by hand). Rebase, never merge, to update your branch:

```
git remote add upstream https://github.com/kubernetes/kubernetes.git
git fetch upstream
git rebase upstream/master            # replay your commits on the latest master
git push -f origin myfeature          # force-push your own branch; never push to upstream
```

If a reviewer asks for a change you disagree with, say why in one paragraph and offer to do it their way if they still prefer it. Being easy to work with is remembered longer than the code.

### Reading a large Go codebase

Start at `main`. In Kubernetes it is `cmd/<binary>/<binary>.go`, which builds a cobra command; the flags live in an `options` package and are copied into a config struct; a `Run` function starts the real work. Follow one flag from the command line to the line that uses it and you have crossed the whole program. Then read the tests next to the file you care about: a table-driven test is a list of inputs and expected outputs, which is the specification the authors actually meant. `go doc ./pkg/controller/deployment` prints the exported API of a package without opening an editor; `go doc k8s.io/client-go/tools/cache.SharedInformer` does the same for a type. When something is slow, `go test -cpuprofile cpu.out` and `go tool pprof cpu.out` show which function spent the time, in a sentence.

### The programmes

**LFX Mentorship** is the Linux Foundation's programme. Projects post mentorship offers; CNCF collects them in the cncf/mentoring repository, where a maintainer files a proposal issue, mentors confirm it, and an admin approves it before it appears on the LFX site. Each term is about 12 weeks of scoped tasks with regular reviews; recent years have run three terms (the repository names them Mar-May, Jun-Aug and Sep-Nov), and the current cycle's folder and dates are in that repository. The LFX eligibility page says you must be 18 or older by the time the programme starts and must not be a prior or active participant in another Linux Foundation mentorship, so in practice you complete one. You may apply to at most three mentorship programmes per term, and withdrawn applications do not count. Stipends vary by programme and by the mentee's country; the programme page states it, so do not assume. Mentors score applicants on skills fit and intent and may interview you. A strong application has a cover letter that names the project's code you have read, links your merged PRs in that project, and shows you understand the task; a letter that could be sent to any project is rejected first.

**Google Summer of Code (GSoC)** is Google's programme for people new to open source: you must be 18 or older at registration, a student or an open source beginner (fewer than 10 issues or PRs on other projects, by Google's definition), and not accepted more than once before. Organisations apply and are announced; contributors discuss ideas with an organisation, then submit up to three proposals through the GSoC site, of which one can be accepted; then about three weeks of community bonding, a coding period of 12 weeks by default (it can run from 8 to 22 weeks if mentor and contributor agree), a midterm evaluation and final submissions. Projects come in sizes of roughly 90, 175 or 350 hours. CNCF applies as one umbrella organisation and lists project ideas in cncf/mentoring; the proposal structure that works is: the problem in the project's words, your plan by week, how you will test it, the PRs you have already merged there, and your availability.

**Hacktoberfest**, every October, is a low-stakes way to practise the fork-PR-review cycle before you aim at a CNCF project. The LFX site and the GSoC site publish the dates for each year; this lesson does not repeat them because they change.

### A 12-week plan from zero to a merged PR

Assume 8 to 10 hours a week alongside classes, one project chosen in week 2, and Go already at the level of lesson 6.

| Week | Do | Result you can show |
| --- | --- | --- |
| 1 | Finish A Tour of Go; write the controller sketch from lesson 25 | A Go program with tests |
| 2 | Install three candidate projects on kind; pick one | A paragraph on why this project |
| 3 | Build from source, run `make test`, read `CONTRIBUTING.md`, sign CLA or set up DCO | Green local build |
| 4 | Read every new issue; reproduce two; comment with findings | Two issue comments with reproductions |
| 5 | First PR: a docs or example fix found in week 3 | PR opened |
| 6 | Join Slack and one community meeting; respond to review on PR 1 | PR 1 merged |
| 7 | Add a unit test for a `good first issue` area | PR 2 opened |
| 8 | Pick a `good first issue` bug; write the failing test first | Reproduction confirmed in the issue |
| 9 | Fix the bug; keep the diff under 100 lines | PR 3 opened |
| 10 | Review rounds; rebase; help triage one more issue | PR 3 merged |
| 11 | Write the LFX or GSoC application with links to PRs 1 to 3 | Application draft reviewed by a mentor on Slack |
| 12 | Submit; start reading the code for the mentorship task | Application in; next issue chosen |

If a PR stalls, do not wait: pick the next task and politely ping once a week with `/assign` to a listed reviewer.

### Putting it on a resume and in interviews

One line per contribution, each a link: project, what changed, what it taught you. "kubernetes-sigs/kind, PR #3412: fixed node image build on arm64 hosts; learned how the kubelet is configured inside a container". Three such lines beat a paragraph about passion. In interviews, tell the story in the order reviewers care about: the bug as a user saw it, how you reproduced it, what the code was doing, the smallest fix, what the reviewer pushed back on and what you changed. Then say what you would do next in that project; that is the answer that shows you will keep going.

## Diagram

Rendering diagram…

## Worked example

**Sizing the 12-week plan, and what a mentorship application looks like from the reviewer's side.**

Budget: 9 hours a week for 12 weeks is 108 hours. Split it as the plan does: weeks 1 to 4 are setup and reading (36 hours), weeks 5 to 10 are three PRs (54 hours, so 18 hours per PR including review rounds), weeks 11 and 12 are the application (18 hours).

Is 18 hours per PR realistic? A docs fix is 2 hours of work and 2 hours of waiting for review spread over a week. A unit test for an existing function is 4 to 6 hours: 2 to read the code, 2 to write the table-driven test, 1 to run `go test ./pkg/... -run TestName -v` and `gofmt`, 1 for review changes. A small bug fix is 8 to 12 hours: 3 to reproduce in a kind cluster, 2 to write the failing test, 2 to fix, 3 across two review rounds. Total for the three: about 18 plus 6 plus 2 is 26 hours of work, leaving 28 hours of slack for a stalled review or a second attempt. The plan holds.

Now the reviewer's side. A mentor for an LFX project on, say, a Prometheus exporter gets 40 applications for one slot. They sort by one question: has this person touched our code? Applications with zero PRs in the project go to the bottom regardless of grades. Applications with one merged docs PR are read. Applications with a merged bug fix plus a comment on the mentorship issue itself ("I read the exporter's collector loop in collector.go; the task's metric is missing because the scrape skips the `/status` endpoint; here is my plan by week") are interviewed. Three merged PRs in 12 weeks puts you in the last group, which is typically a handful of people.

The same arithmetic explains why starting in week 1 of a term is too late: the proposal windows close before the term, and the PRs must be merged before that. Start one term ahead, which is what the 12-week plan assumes.

## Runnable code

Go · gofmt and go vet clean · runs and prints its own checks

```
// A small contribution report, standard library only.
//
// It parses a sample `git log --name-only` output (embedded as a string) and
// a few fake pull request records, then prints: PRs by state, median review
// turnaround, and the files touched most. The same file carries
// table-driven tests that run from main and print PASS lines, which is the
// shape of most tests you will read and write in a Go CNCF project.
package main

import (
	"fmt"
	"os"
	"sort"
	"strings"
	"time"
)

// gitLog is what `git log --author=you --date=short --name-only
// --pretty=format:'commit %h%nDate: %ad%nSubject: %s'` prints.
const gitLog = `commit a1f2c3d
Date: 2026-09-02
Subject: docs: fix typo in README quick start

README.md

commit b2e3d4f
Date: 2026-09-14
Subject: test: add unit test for queue requeue backoff

pkg/queue/queue_test.go

commit c3f4e5a
Date: 2026-09-28
Subject: fix: requeue key after transient API error

pkg/queue/queue.go
pkg/queue/queue_test.go

commit d4a5b6c
Date: 2026-10-10
Subject: feat: add --metrics-addr flag to controller

cmd/controller/main.go
pkg/queue/queue.go
docs/flags.md
`

type Commit struct {
	Hash    string
	Date    string
	Subject string
	Files   []string
}

// parseGitLog turns the text above into Commit values. It is deliberately
// strict: an unknown line before the first "commit" is an error.
func parseGitLog(text string) ([]Commit, error) {
	var out []Commit
	var cur *Commit
	for n, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		switch {
		case strings.HasPrefix(line, "commit "):
			out = append(out, Commit{Hash: strings.TrimPrefix(line, "commit ")})
			cur = &out[len(out)-1]
		case cur == nil && line == "":
			continue
		case cur == nil:
			return nil, fmt.Errorf("line %d: %q before any commit header", n+1, line)
		case strings.HasPrefix(line, "Date: "):
			cur.Date = strings.TrimPrefix(line, "Date: ")
		case strings.HasPrefix(line, "Subject: "):
			cur.Subject = strings.TrimPrefix(line, "Subject: ")
		case line == "":
			continue
		default:
			cur.Files = append(cur.Files, line)
		}
	}
	return out, nil
}

// PR is a fake pull request record as a project tracker might export it.
type PR struct {
	Number    int
	Title     string
	State     string // open, merged, closed
	Opened    string // YYYY-MM-DD
	FirstRevw string // date of the first maintainer review, "" if none yet
}

var prs = []PR{
	{101, "docs: fix typo in README quick start", "merged", "2026-09-02", "2026-09-03"},
	{108, "test: add unit test for queue requeue backoff", "merged", "2026-09-14", "2026-09-19"},
	{115, "fix: requeue key after transient API error", "merged", "2026-09-28", "2026-10-01"},
	{122, "feat: add --metrics-addr flag to controller", "open", "2026-10-10", "2026-10-17"},
	{123, "chore: bump golangci-lint", "closed", "2026-10-12", ""},
}

func countByState(ps []PR) map[string]int {
	m := map[string]int{}
	for _, p := range ps {
		m[p.State]++
	}
	return m
}

// reviewDays returns the days from opening to first review, for PRs that got one.
func reviewDays(ps []PR) ([]int, error) {
	var days []int
	for _, p := range ps {
		if p.FirstRevw == "" {
			continue
		}
		a, err := time.Parse("2006-01-02", p.Opened)
		if err != nil {
			return nil, err
		}
		b, err := time.Parse("2006-01-02", p.FirstRevw)
		if err != nil {
			return nil, err
		}
		days = append(days, int(b.Sub(a).Hours()/24))
	}
	return days, nil
}

func median(xs []int) float64 {
	if len(xs) == 0 {
		return 0
	}
	s := append([]int(nil), xs...)
	sort.Ints(s)
	n := len(s)
	if n%2 == 1 {
		return float64(s[n/2])
	}
	return float64(s[n/2-1]+s[n/2]) / 2
}

type fileCount struct {
	File  string
	Count int
}

func filesTouched(cs []Commit) []fileCount {
	m := map[string]int{}
	for _, c := range cs {
		for _, f := range c.Files {
			m[f]++
		}
	}
	out := make([]fileCount, 0, len(m))
	for f, n := range m {
		out = append(out, fileCount{f, n})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Count != out[j].Count {
			return out[i].Count > out[j].Count
		}
		return out[i].File < out[j].File
	})
	return out
}

// ---------- table-driven tests, run from main ----------

type tcase struct {
	name string
	run  func() error
}

func runTests(cases []tcase) bool {
	ok := true
	for _, c := range cases {
		if err := c.run(); err != nil {
			fmt.Printf("FAIL: %s: %v\n", c.name, err)
			ok = false
			continue
		}
		fmt.Printf("PASS: %s\n", c.name)
	}
	return ok
}

func expect(cond bool, format string, a ...any) error {
	if cond {
		return nil
	}
	return fmt.Errorf(format, a...)
}

func tests() []tcase {
	return []tcase{
		{"parse: four commits with files", func() error {
			cs, err := parseGitLog(gitLog)
			if err != nil {
				return err
			}
			if err := expect(len(cs) == 4, "got %d commits, want 4", len(cs)); err != nil {
				return err
			}
			return expect(len(cs[3].Files) == 3, "last commit touched %d files, want 3", len(cs[3].Files))
		}},
		{"parse: rejects text before the first commit", func() error {
			_, err := parseGitLog("Date: 2026-01-01\ncommit x\n")
			return expect(err != nil, "expected an error, got nil")
		}},
		{"parse: empty input gives no commits and no error", func() error {
			cs, err := parseGitLog("")
			if err != nil {
				return err
			}
			return expect(len(cs) == 0, "got %d commits, want 0", len(cs))
		}},
		{"median: odd, even and empty", func() error {
			for _, tt := range []struct {
				in   []int
				want float64
			}{
				{[]int{1, 5, 3}, 3},
				{[]int{1, 5, 3, 7}, 4},
				{nil, 0},
			} {
				if got := median(tt.in); got != tt.want {
					return fmt.Errorf("median(%v) = %v, want %v", tt.in, got, tt.want)
				}
			}
			return nil
		}},
		{"reviewDays: skips PRs with no review", func() error {
			d, err := reviewDays(prs)
			if err != nil {
				return err
			}
			return expect(len(d) == 4, "got %d reviewed PRs, want 4", len(d))
		}},
		{"filesTouched: most-touched file first, ties by name", func() error {
			ft := filesTouched([]Commit{{Files: []string{"b.go", "a.go"}}, {Files: []string{"b.go"}}})
			if err := expect(ft[0].File == "b.go" && ft[0].Count == 2, "first = %+v", ft[0]); err != nil {
				return err
			}
			return expect(ft[1].File == "a.go", "second = %+v", ft[1])
		}},
	}
}

func main() {
	fmt.Println("== tests ==")
	if !runTests(tests()) {
		os.Exit(1)
	}

	fmt.Println("\n== contribution report ==")
	commits, err := parseGitLog(gitLog)
	if err != nil {
		fmt.Println("parse error:", err)
		os.Exit(1)
	}
	fmt.Printf("commits: %d (%s to %s)\n", len(commits), commits[0].Date, commits[len(commits)-1].Date)

	byState := countByState(prs)
	states := make([]string, 0, len(byState))
	for s := range byState {
		states = append(states, s)
	}
	sort.Strings(states)
	fmt.Print("PRs by state:")
	for _, s := range states {
		fmt.Printf(" %s=%d", s, byState[s])
	}
	fmt.Println()

	days, _ := reviewDays(prs)
	fmt.Printf("days to first review: %v, median %.1f\n", days, median(days))

	fmt.Println("files touched:")
	for _, fc := range filesTouched(commits) {
		fmt.Printf("  %-32s %d\n", fc.File, fc.Count)
	}

	// The ladder, as the report shows it: docs, then tests, then a fix, then a feature.
	fmt.Println("ladder:")
	for _, c := range commits {
		kind := strings.SplitN(c.Subject, ":", 2)[0]
		fmt.Printf("  %s  %-5s %s\n", c.Date, kind, c.Subject)
	}
}
```

## Key takeaways

* A merged PR with a public review thread is a work sample; it shows reading, process, review and finishing at once.
* CNCF projects are run by maintainers in OWNERS files; Kubernetes splits work into SIGs, designs big changes as KEPs, and releases about three times a year.
* Kubernetes requires a signed CLA; many other projects use DCO sign-off with git commit -s. Read CONTRIBUTING.md first.
* Prow is the CI and the bot: /retest, /assign, /lgtm from a reviewer and /approve from an approver, then the merge bot merges.
* Pick a project by using it, building it and reading its issues for a week; smaller projects review faster than Kubernetes core.
* Climb in order: docs, tests, triage, small fixes, features, reviews, membership. Mentorships select on the lower steps already being done.
* LFX Mentorship runs terms of about 12 weeks with up to three applications per term; GSoC is for beginners, 18 or older, with up to three proposals. Neither replaces prior PRs in the project.
* Keep PRs small, test first, answer every review comment, rebase instead of merge, and put each merged PR on the resume as a link with one line on what it taught you.

## Common mistakes

* Opening a PR before reading CONTRIBUTING.md, so it fails the CLA or DCO check and sits unreviewed.
* Choosing kubernetes/kubernetes for the first PR and giving up when review takes weeks; start with a smaller CNCF project.
* A first PR that refactors 800 lines "while I was there"; reviewers decline it and remember the name.
* Applying to LFX or GSoC with a generic cover letter and no PRs in that project; mentors sort those to the bottom.
* Commenting /retest on a real failure instead of reading the CI log, which wastes CI and annoys reviewers.
* Treating a review comment as an argument to win; agree, explain in one paragraph, or ask, then move on.

## Practice

* Install one CNCF project (KEDA, cert-manager or Flux) on a kind cluster, build it from source, run its unit tests, and record the time to a green `make test`. Measure: a working local build and one sentence on the first thing you would fix in its developer docs.
* Pick an open `good first issue` in that project, reproduce it on kind, and post a comment with your exact steps and output. Measure: a maintainer reacts or replies within two weeks; if not, pick another.
* Open a docs or test PR in the same project with CLA or DCO done, respond to every review comment within a day, and rebase at least once. Measure: the PR is merged, and you can explain every line of the review thread.
* Write the first draft of an LFX or GSoC application for a listed cncf/mentoring project: the files you read, your plan by week, your PR links. Measure: a mentor or Slack channel member gives feedback on it before the window opens.

## Interview questions (10)

1.Tell me about an open source contribution you made.Easy

I say what the user-facing bug was, how I reproduced it on a kind cluster, what the code was doing wrong, the smallest fix, and what the reviewer asked me to change. For example: a docs example used a flag that had been renamed, so I fixed the example and, while reproducing, found the deprecation warning text was wrong too; the reviewer asked me to split that into a second PR, which taught me that one PR does one thing. Then I say what I would do next in that project, because the interviewer wants to know I will keep contributing.

2.What is the difference between a CLA and DCO, and which does Kubernetes use?Easy

A Contributor License Agreement is a document you sign once, as an individual or through your employer, granting the project the rights it needs to use your contribution; Kubernetes requires it through the Linux Foundation's EasyCLA, and a bot blocks the PR until it is signed. The Developer Certificate of Origin is a per-commit statement that you have the right to submit the code, added as a Signed-off-by line with git commit -s. Many CNCF projects use DCO because it needs no paperwork. The project's CONTRIBUTING.md says which applies.

3.How does a pull request get merged in Kubernetes?Medium

CI is Prow, and the bot drives the flow. If I am not an org member, a member must comment /ok-to-test before tests run. A reviewer listed in the OWNERS file for the changed directory reviews and comments /lgtm, which adds the lgtm label. An approver from the same OWNERS file comments /approve, which adds the approved label. When both labels are present, the CLA check passes and the required jobs are green, the merge bot called tide merges the PR; nobody clicks the merge button. If a job fails from flakiness I can comment /retest, but only after checking the log.

4.How would you pick a CNCF project to contribute to?Medium

I would install two or three candidates on a kind cluster and use each for its real purpose, because I can only fix what I understand as a user. Then I would build the one I liked from source, run its tests, and read its issues for a week, reproducing a couple, to learn the vocabulary and see which maintainers respond. I would prefer a project with recent good first issue labels and a reasonable review turnaround, such as KEDA or cert-manager, over Kubernetes core for the first PR. Finally I would join its Slack channel and attend one meeting before opening anything.

5.What makes a PR easy to review?Easy

Small scope, one change, with the test that failed before the fix. A description that says what and why in three sentences, links the issue with Fixes #N, and fills the release note if users will notice. Commits that build individually. During review, I answer every comment, push fix-up commits so the reviewer sees only the deltas, and squash at the end if the project asks. I rebase on upstream instead of merging, so the history stays linear. The Kubernetes guide puts it as preferring 100 small, obvious PRs over 10 monoliths.

6.What does a strong LFX Mentorship application contain?Medium

Links to merged PRs in that specific project, because mentors sort applications by whether the person has touched their code. A cover letter that names the files I read for the mentorship task, states what I think the task involves and a plan by week, and is honest about what I do not know yet. My skills listed as the LFX profile asks, matching the technologies the programme lists. Availability for the 12 weeks. And a comment on the mentorship issue before applying, so the mentor already knows my name when the applications arrive.

7.Who can apply to GSoC, and how is it different from LFX?Medium

GSoC is Google's programme for people new to open source: you must be 18 or older at registration, and a student or an open source beginner by Google's definition, which is roughly fewer than 10 issues or PRs on other projects, and you cannot have been accepted more than once before. You submit up to three proposals through the GSoC site, one can be accepted, and projects are sized at about 90, 175 or 350 hours. LFX is run by the Linux Foundation, has terms of about 12 weeks, allows up to three applications per term, and is not limited to beginners, but prior or active participants in another Linux Foundation mentorship are not eligible, so you complete one. CNCF participates in both through its cncf/mentoring repository.

8.How do you start reading a codebase of a million lines?Medium

I start at main and follow one flag. In Kubernetes, cmd/kube-controller-manager builds a cobra command, the flags fill an options struct, and a Run function starts the controllers; following one flag to where it is used crosses the whole program. Then I read the tests next to the code I care about, because a table-driven test is the specification the authors meant. I use go doc on a package to see its exported API without opening the files, and grep for an error string I saw in production to find the line that produced it. I do not try to read it all.

9.What is a KEP and when would you write one?Easy

A Kubernetes Enhancement Proposal is a design document in the kubernetes/enhancements repository for any change that a blog post would be written about, that needs several SIGs, or that moves a feature between alpha, beta and GA. It has motivation, goals and non-goals, the design, test plan and graduation criteria, and it must be accepted by the owning SIG before implementation, with deadlines tied to the release cycle. I would write one for a new field or behaviour in a core API; a bug fix or a docs change never needs one.

10.A reviewer asks for a change you think is wrong. What do you do?Easy

I assume they know something I do not, and I ask or explain once, in one paragraph, with the specific reason: a test that would break, a behaviour a user depends on, a cost. If they still prefer their way, I do it their way, because they own the code and will maintain it after I leave, and being easy to work with is what gets the next PR reviewed quickly. If the question is genuinely open, I suggest taking it to the issue or the SIG meeting so more people can weigh in.

## Quiz

1.Which legal step does Kubernetes require before your first PR can merge?

2.Which two labels, plus green CI, cause the Kubernetes merge bot to merge a PR?

3.What does a strong LFX Mentorship application have that a weak one lacks?

4.According to the Kubernetes contributor guide, which is preferred?

5.Who is eligible for GSoC as a contributor?

## Practice these problems

* [DESIGNObservability platform for 200 microservicesHard](/devops/problems/observability-platform)
* [CODEHelm chart from scratch with values, templates and a testMedium](/devops/problems/helm-chart-from-scratch)
* [CODEGo: a Kubernetes-style reconcile loop for a custom resourceHard](/devops/problems/go-reconcile-loop)

## Further reading

* [Kubernetes contributor guide: Getting StartedGuidekubernetes.dev](https://www.kubernetes.dev/docs/guide/)
* [kubernetes/community: Kubernetes Community DocumentationGuidegithub.com](https://github.com/kubernetes/community)
* [LFX MentorshipGuidementorship.linuxfoundation.org](https://mentorship.linuxfoundation.org/)
* [Google Summer of CodeGuidesummerofcode.withgoogle.com](https://summerofcode.withgoogle.com/)
* [cncf/mentoring: CNCF Mentoring + LFX + Summer of CodeGuidegithub.com](https://github.com/cncf/mentoring)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousKubernetes internals and operators in Go](/devops/learn/kubernetes-internals-operators-go)[NextCloud cost and FinOps](/devops/learn/cloud-cost-and-finops)

## On this page

1. [Lesson](#lesson)
2. [Diagram](#diagram)
3. [Worked example](#example)
4. [Code](#code)
5. [Key takeaways](#takeaways)
6. [Common mistakes](#mistakes)
7. [Practice](#practice)
8. [Interview questions](#interview)
9. [Quiz](#quiz)
10. [Related problems](#problems)
11. [Further reading](#reading)
12. [My notes](#notes)

## In this lesson

1. [Why contribution is the strongest signal](#why-contribution-is-the-strongest-signal)
2. [The CNCF projects to know, by category](#the-cncf-projects-to-know-by-category)
3. [How a CNCF project is run](#how-a-cncf-project-is-run)
4. [How to pick a project](#how-to-pick-a-project)
5. [The contribution ladder](#the-contribution-ladder)
6. [Writing a good issue and a good PR](#writing-a-good-issue-and-a-good-pr)
7. [Reading a large Go codebase](#reading-a-large-go-codebase)
8. [The programmes](#the-programmes)
9. [A 12-week plan from zero to a merged PR](#a-12-week-plan-from-zero-to-a-merged-pr)
10. [Putting it on a resume and in interviews](#putting-it-on-a-resume-and-in-interviews)
