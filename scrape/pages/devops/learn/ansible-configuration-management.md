# Ansible and configuration management — DevOps roadmap · FAANGrind

Source: https://faangrind.vercel.app/devops/learn/ansible-configuration-management

[DevOps roadmap](/devops)

Cloud and IaCLesson #14SkimBeginner 1.5 h

# Ansible and configuration management

Configuration management is the job of making a fleet of machines match a written description: these packages, this config file, this service running. Ansible does it over SSH with no agent, from YAML playbooks whose tasks are idempotent: run them twice and the second run changes nothing. This lesson covers where Ansible still fits once you have containers and Terraform, its model (inventory, plays, tasks, modules, handlers, roles, vault) and the mistakes that make it dangerous.

ansibleconfiguration managementidempotencysshlinuxvm fleets

## Why it matters

Ansible is a SKIM topic because Kubernetes and image builds took over most of what it used to do. It still shows up in interviews at companies with VM fleets, on-prem racks or bastion hosts, and in the question "what is idempotency" which every DevOps interview asks in some form. In real work you will meet it when bootstrapping nodes, patching a hundred VMs, or inheriting a system built before containers. Knowing the model, and knowing when not to reach for it, is enough.

Read first: [Linux for operators](/devops/learn/linux-for-operators), [Bash scripting and the terminal toolkit](/devops/learn/bash-and-terminal-toolkit), [Terraform - infrastructure as code](/devops/learn/terraform-infrastructure-as-code)

## Lesson

### What is left for configuration management

Before containers, every server was configured in place: install the runtime, write the config, start the service. Configuration management tools did that repeatably. Puppet and Chef solved it with an agent on every machine pulling from a server; they are rarely chosen for new work now. Ansible won because it needs nothing on the target but SSH and Python.

Today, containers carry their own configuration and Terraform creates the machines, so what is left is smaller but real:

| Still Ansible's job | Why containers and Terraform do not cover it |
| --- | --- |
| VM fleets that run things outside Kubernetes: databases on EC2, legacy apps, Windows hosts | Something must install and configure the software on the box |
| Bastion and jump hosts, build agents, on-prem servers | Few, long-lived, hand-tuned, and nobody will containerise them |
| The node image itself (hardening, agents, kernel settings) | Built once with Packer, which calls Ansible as a provisioner |
| Bootstrapping: the first config a fresh VM needs before anything else can run | Terraform hands over a bare machine |
| One-off fleet operations: rotate a key on 200 hosts, patch a CVE, collect a file | An ad hoc loop over SSH, but with inventory, parallelism and a report |

Anything Kubernetes already does, such as rolling out an application, scaling, restarts and health checks, is not Ansible's job.

### The model

Ansible is **agentless**: a control machine (your laptop or a CI runner) connects over SSH to each host and runs small Python programs called **modules**. Nothing is installed on the targets. The parts, top down:

* **Inventory** lists hosts in groups. Static INI or YAML, or a **dynamic** plugin that asks the AWS API, so new EC2 instances appear automatically.
* A **playbook** is a YAML file of **plays**; each play targets a group of hosts and runs a list of **tasks** in order.
* A **task** calls one module with parameters. The module checks the current state and changes only what differs, then reports `changed` or `ok`. That is **idempotency**: the second run is all `ok`.
* A **handler** is a task that runs once at the end of the play, only if a task that `notify`s it reported `changed`. "Restart nginx only if the config changed" is the classic use.
* **Variables** come from many places; the rule to remember is that role `defaults/` is the weakest, `group_vars` and `host_vars` sit in the middle, and `-e` extra vars on the command line always win.
* **Templates** are Jinja2 files (`site.conf.j2`) rendered with variables, written by the `template` module.
* A **role** is a reusable unit with a fixed layout: `tasks/main.yml`, `handlers/main.yml`, `templates/`, `files/`, `defaults/main.yml`, `vars/main.yml`, `meta/main.yml`.
* **Collections** package roles, modules and plugins; Galaxy is the registry. `ansible-galaxy collection install community.general` gives you the `ufw` module used below. Modules are called by their full name, `ansible.builtin.apt`.
* **ansible-vault** encrypts a whole vars file or one value (`ansible-vault encrypt_string`), which appears in YAML as `!vault |`; the password comes from `--ask-vault-pass` or `--vault-password-file`.
* `--check` simulates a run and `--diff` shows the before and after of a template; `--tags config` runs a subset; `--limit web-3` restricts hosts; `serial: 1` makes a play finish on one host before starting the next, which is a rolling change.

### A complete playbook

Inventory, `inventory/prod.ini`:

```
[webservers]
web-1 ansible_host=10.0.1.11
web-2 ansible_host=10.0.1.12
web-3 ansible_host=10.0.1.13

[webservers:vars]
ansible_user=ubuntu
```

Playbook, `site.yml`: installs Nginx, templates its config, opens the firewall and restarts the service only when the config changed, one host at a time.

```
- name: Configure web servers
  hosts: webservers
  become: true            # sudo for every task; forgetting this is mistake number one
  serial: 1               # one host at a time: a bad config takes down one server, not three
  any_errors_fatal: true  # stop the whole run at the first failed host
  vars:
    nginx_port: 80
    site_root: /var/www/html
  tasks:
    - name: Install nginx
      ansible.builtin.apt:
        name: nginx
        state: present
        update_cache: true
        cache_valid_time: 3600
      tags: [packages]

    - name: Template the site config
      ansible.builtin.template:
        src: templates/site.conf.j2
        dest: /etc/nginx/sites-enabled/default
        owner: root
        group: root
        mode: "0644"
      notify: Restart nginx          # only fires if this task reports changed
      tags: [config]

    - name: Check the nginx config
      ansible.builtin.command: nginx -t
      changed_when: false            # a read-only command must not report changed

    - name: Open the firewall
      community.general.ufw:
        rule: allow
        port: "{{ nginx_port }}"
        proto: tcp

    - name: Enable and start nginx
      ansible.builtin.systemd_service:
        name: nginx
        enabled: true
        state: started

  handlers:
    - name: Restart nginx
      ansible.builtin.systemd_service:
        name: nginx
        state: restarted
```

Template, `templates/site.conf.j2`:

```
server {
    listen {{ nginx_port }};
    root {{ site_root }};
    server_name {{ inventory_hostname }};
}
```

Run it:

```
ansible-playbook -i inventory/prod.ini site.yml --check --diff --limit web-1   # dry run on one host first
ansible-playbook -i inventory/prod.ini site.yml                                 # for real, serial: 1
ansible-playbook -i inventory/prod.ini site.yml --tags config                   # only the template task
```

The recap on the first run shows `changed=5` per host (four tasks plus the handler); the second run shows `changed=0` and the handler does not run, because nothing notified it.

For AWS, replace the INI file with `inventory/aws_ec2.yml` (the file name must end in `aws_ec2.yml`): `plugin: amazon.aws.aws_ec2`, a `regions` list, `filters` such as `tag:Role: web`, and `keyed_groups` with `key: ec2_tags.Role` so instances land in groups by tag.

### Ansible next to Terraform and Packer

| Question | Terraform | Ansible | Packer |
| --- | --- | --- | --- |
| What it does | Creates the machine, network, load balancer | Configures what is inside a running machine | Builds a machine image once |
| Model | Declarative with a state file | Imperative tasks that are each idempotent; no state | Declarative build, runs provisioners (Ansible, shell) |
| When it runs | On every infra change | On every config change, or on boot | Once per image version |
| Typical pair | Terraform creates an ASG from a Packer AMI | Ansible, called by Packer, hardens the AMI | Immutable: replace the instance instead of patching it |

The modern default is **immutable infrastructure**: bake the image with Packer and Ansible, roll new instances with Terraform, never SSH in to change a live box. Running Ansible against live fleets is for the cases in the first table, and for the one-off operations.

### Common mistakes

* `ansible.builtin.shell: apt-get install -y nginx` reports `changed` every run and fires the handler every run. Use the `apt` module, or add `creates:` or `changed_when:` to a command.
* Forgetting `become: true` and getting "Permission denied" halfway through a play, with the first tasks already applied.
* Running against prod without `--limit` and `--check` first: an inventory typo makes `hosts: all` mean every machine in the account.
* A handler that restarts a service on every host at once because the play has no `serial`.
* Secrets in plain `group_vars` committed to Git instead of vault, or `--vault-password-file` pointing at a file inside the repo.
* Using Ansible to deploy a container to Kubernetes. That is Helm and Argo CD's job; Ansible stops at the node.

## Diagram

Rendering diagram…

## Worked example

**Rolling a config change across 30 web servers.** The playbook above is run with `serial: 3` after the Nginx template changed in Git. Each host needs about 4 seconds for the five tasks over SSH, plus a 2-second Nginx restart from the handler.

Step 1: batches. 30 hosts at 3 per batch is 10 batches. Inside a batch the 3 hosts run in parallel (the default `forks` is 5, so 3 fit), and the play, including the handler, finishes on the batch before the next one starts.

Step 2: time. Per batch: 4 seconds of tasks plus 2 seconds of restart, about 6 seconds. 10 batches give about 60 seconds for the whole fleet. With `serial: 1` it would be 30 batches, about 3 minutes; with no `serial`, 30 hosts run through the default 5 forks, so about 6 waves of 6 seconds, roughly 36 seconds, but every host restarts Nginx within the same minute and a bad config takes all 30 down together.

Step 3: capacity during the roll. With 3 hosts restarting at any moment, 27 of 30 serve traffic: 90 percent capacity, which is why batch size is chosen from the load headroom. If peak load needs 25 hosts, `serial: 3` is safe and `serial: 10` is not.

Step 4: failure. The template on batch 2 renders a bad `listen` line. `nginx -t` fails on those 3 hosts and they drop out of the play. The docs say `serial` changes the scope of a failure to the batch, and with `any_errors_fatal: true` on the play Ansible stops the whole run at that point, so the other 24 hosts never receive the broken file. The handler never fired on the failing hosts because the play did not reach its end there, so even they still run the old config. Fix the template, rerun with `--limit` to the failed hosts first, then the rest; every unchanged host reports `ok` and nothing restarts twice.

## Runnable code

Python · runs and prints its own checks

```
"""A tiny idempotent configuration applier, the idea behind every Ansible module.

Each task describes a desired state (a file's content, a package installed,
a service enabled). Applying it means: look at the host, compare, change only
if needed, and report 'changed' or 'ok'. Handlers run once at the end of the
play, and only if a task that notifies them reported changed.

Everything is in memory; no SSH, no network. Running the same play twice shows
the point: changed on the first run, ok on the second, handler fires only once.
"""

class Host:
    """An in-memory machine: files, installed packages, services."""

    def __init__(self, name):
        self.name = name
        self.files = {}          # path -> content
        self.packages = set()    # installed package names
        self.services = {}       # name -> {"enabled": bool, "running": bool, "restarts": int}

# Modules: each takes (host, params) and returns (changed, message).
# The rule for every module is the same: read the current state first,
# do nothing if it already matches, never blindly run the change.

def file_module(host, params):
    path, content = params["path"], params["content"]
    if host.files.get(path) == content:
        return False, f"{path} already has the desired content"
    host.files[path] = content
    return True, f"wrote {path}"

def package_module(host, params):
    name, state = params["name"], params.get("state", "present")
    installed = name in host.packages
    if state == "present" and installed:
        return False, f"{name} already installed"
    if state == "absent" and not installed:
        return False, f"{name} already absent"
    if state == "present":
        host.packages.add(name)
        return True, f"installed {name}"
    host.packages.discard(name)
    return True, f"removed {name}"

def service_module(host, params):
    name = params["name"]
    svc = host.services.setdefault(name, {"enabled": False, "running": False, "restarts": 0})
    changed = []
    if "enabled" in params and svc["enabled"] != params["enabled"]:
        svc["enabled"] = params["enabled"]
        changed.append("enabled" if params["enabled"] else "disabled")
    state = params.get("state")
    if state == "started" and not svc["running"]:
        svc["running"] = True
        changed.append("started")
    elif state == "restarted":            # like Ansible: restarted always changes
        svc["running"] = True
        svc["restarts"] += 1
        changed.append("restarted")
    if not changed:
        return False, f"{name} already in desired state"
    return True, f"{name} {' and '.join(changed)}"

def shell_module(host, params):
    """The non-idempotent trap: a raw command always reports changed."""
    return True, f"ran: {params['cmd']}"

MODULES = {"file": file_module, "package": package_module, "service": service_module, "shell": shell_module}

def run_play(host, tasks, handlers):
    """Apply tasks in order, collect notifications, run notified handlers once at the end."""
    counts = {"ok": 0, "changed": 0}
    notified = []  # ordered, no duplicates
    for task in tasks:
        changed, msg = MODULES[task["module"]](host, task["params"])
        status = "changed" if changed else "ok"
        counts[status] += 1
        print(f"  TASK [{task['name']:<32}] {status:<8} {msg}")
        if changed and task.get("notify") and task["notify"] not in notified:
            notified.append(task["notify"])
    for name in notified:
        changed, msg = MODULES[handlers[name]["module"]](host, handlers[name]["params"])
        print(f"  HANDLER [{name:<29}] changed  {msg}")
        counts["changed"] += 1
    print(f"  RECAP {host.name}: ok={counts['ok']} changed={counts['changed']} handlers_run={len(notified)}")
    return counts, notified

NGINX_CONF = "server { listen 80; root /var/www/html; }\n"

TASKS = [
    {"name": "Install nginx", "module": "package", "params": {"name": "nginx", "state": "present"}},
    {"name": "Write nginx site config", "module": "file",
     "params": {"path": "/etc/nginx/sites-enabled/default", "content": NGINX_CONF},
     "notify": "Restart nginx"},
    {"name": "Write index page", "module": "file",
     "params": {"path": "/var/www/html/index.html", "content": "<h1>hello</h1>\n"}},
    {"name": "Enable and start nginx", "module": "service",
     "params": {"name": "nginx", "enabled": True, "state": "started"}},
]

HANDLERS = {
    "Restart nginx": {"module": "service", "params": {"name": "nginx", "state": "restarted"}},
}

if __name__ == "__main__":
    web = Host("web-1")

    print("PLAY 1: fresh host")
    c1, n1 = run_play(web, TASKS, HANDLERS)
    assert c1 == {"ok": 0, "changed": 5}, c1          # 4 tasks changed + 1 handler
    assert n1 == ["Restart nginx"]
    assert web.services["nginx"]["restarts"] == 1

    print("\nPLAY 2: same play again, nothing should change")
    c2, n2 = run_play(web, TASKS, HANDLERS)
    assert c2 == {"ok": 4, "changed": 0}, c2
    assert n2 == []                                    # handler not notified, so not run
    assert web.services["nginx"]["restarts"] == 1      # still 1: no needless restart

    print("\nPLAY 3: config changed in Git, only the file task and the handler fire")
    tasks_v2 = [dict(t) for t in TASKS]
    tasks_v2[1] = dict(tasks_v2[1], params={"path": "/etc/nginx/sites-enabled/default",
                                            "content": NGINX_CONF.replace("80", "8080")})
    c3, n3 = run_play(web, tasks_v2, HANDLERS)
    assert c3 == {"ok": 3, "changed": 2}, c3           # 1 task + 1 handler
    assert web.services["nginx"]["restarts"] == 2

    print("\nPLAY 4: the shell-task mistake, changed every time even though nothing changed")
    bad = [{"name": "Install nginx with a shell command", "module": "shell",
            "params": {"cmd": "apt-get install -y nginx"}, "notify": "Restart nginx"}]
    c4, n4 = run_play(web, bad, HANDLERS)
    assert c4["changed"] == 2 and web.services["nginx"]["restarts"] == 3
    print("\nself-checks passed: idempotent modules report ok on the second run, the handler ran "
          "only when its notifying task changed, and the shell task restarted nginx for nothing")
```

## Key takeaways

* Configuration management puts a machine into a described state; Ansible does it over SSH with no agent on the target.
* Idempotency is the whole point: a module compares desired with current state and reports changed or ok, so a second run is harmless.
* Handlers run once at the end of a play and only when a notifying task changed; that is how you restart a service only when its config changed.
* Inventory groups hosts; dynamic AWS inventory builds groups from EC2 tags; roles and collections make playbooks reusable; vault keeps secrets encrypted in Git.
* `--check --diff --limit` before every prod run; `serial` for rolling changes so a bad config hits one batch, not the fleet.
* Terraform creates machines, Packer bakes images, Ansible configures what is inside; Kubernetes workloads are not Ansible's job.
* Puppet and Chef solved the same problem with agents and are rarely chosen for new work.

## Common mistakes

* Shell and command tasks that are not idempotent, so every run reports changed and every run restarts services.
* Missing `become: true`, discovered halfway through a play with the first tasks already applied.
* Running against prod with `hosts: all` and no `--limit` or `--check`, after an inventory change nobody re-read.
* No `serial`, so the handler restarts the service on every host in the same second.
* Treating Ansible as a deployment tool for Kubernetes instead of stopping at the node.

## Practice

* Run the applier script from this lesson, then add a `user` module that creates a login only if missing and confirm the second run reports ok.
* Start two Ubuntu containers with SSH (or two Multipass VMs), write an INI inventory, and run the Nginx playbook with `--check --diff` first, then for real, then again; confirm the recap shows changed=0 the third time and the handler did not run.
* Change the template port to 8080 and rerun with `--tags config`; confirm only the template task and the handler report changed, and curl the new port.
* Encrypt a variable with `ansible-vault encrypt_string`, put it in `group_vars/webservers.yml`, and run the playbook with `--ask-vault-pass`; then try without it and read the error.

## Interview questions (7)

1.Ansible or Terraform: what is the difference and when do you use each?Easy

Terraform provisions infrastructure: it creates VPCs, instances, databases and DNS records through cloud APIs, keeps a state file, and shows a plan of exactly what will change before it applies. It is declarative and best at the lifecycle of cloud resources, including deleting them. Ansible configures machines that already exist: it connects over SSH with no agent and runs tasks, such as installing packages, writing config files from templates and restarting services, in order. It has no state file; it checks the machine each time. They work together: Terraform creates the EC2 instances and outputs their addresses, and Ansible (through a dynamic inventory) configures them. In a container platform Ansible's role shrinks, because the image is built once (with Packer or a Dockerfile) and Kubernetes runs it, but it is still the right tool for VM fleets, bastions and one-off changes across many hosts.

2.What does idempotent mean in Ansible and why does it matter?Easy

An idempotent task gives the same result however many times you run it, and only reports changed when it actually changed something. The apt module checks whether nginx is installed before installing; the template module compares the rendered file with the one on disk before writing. It matters for two reasons. You can rerun a playbook safely to converge a host that failed halfway, and handlers depend on it: if a task falsely reports changed every run, the service restarts every run. The common way to break it is a shell or command task; the fix is the proper module, or creates and changed\_when on the command.

3.How does a handler differ from a normal task?Easy

A handler is defined in the handlers section and does not run on its own. A task names it with notify, and the handler runs only if that task reported changed. All notified handlers run once at the end of the play, after every task, even if five tasks notified the same one, so Nginx restarts once rather than five times. meta flush\_handlers runs them earlier if you need to. The typical pair is a template task that writes a config and notifies a restart handler, so a run that changes nothing restarts nothing.

4.When would you choose Ansible over Terraform, and when the reverse?Medium

They answer different questions. Terraform creates and tracks cloud resources: VPCs, instances, load balancers, IAM. It is declarative with a state file, so it knows what to delete. Ansible configures what is inside a running machine: packages, config files, users, services. It has no state; each task is idempotent on its own. I use Terraform for everything the cloud API owns and Ansible for anything that needs SSH into a box, usually only VM fleets, bastions and on-prem. For most modern setups the box is a Packer image built with Ansible once and rolled out with Terraform, so Ansible never touches a live server.

5.You have to patch a package on 200 production VMs. How do you run it safely?Medium

First a dry run: ansible-playbook with --check and --diff and --limit to one canary host, and read the output. Then run for real on that one host with --limit and verify the service. Then the fleet with serial set to a batch size the load headroom allows, perhaps 10 percent, so a failure stops the run after one batch instead of touching all 200. The play uses the apt or dnf module with a pinned version, not a shell task, so a rerun on failed hosts is safe and reports ok on the hosts already done. Secrets, if any, come from vault, and the run happens from a CI runner with a logged job, not from a laptop.

6.What does Ansible need on the target hosts, and how does it connect?Easy

Only SSH access and a Python interpreter, which every common Linux image has. There is no agent. The control node reads the inventory, opens SSH connections in parallel, the default forks is 5, copies each module as a small Python program to a temporary directory on the host, runs it with the parameters from the task, reads the JSON result, and deletes it. Privilege escalation is become, which runs sudo on the host. For Windows it uses WinRM instead of SSH. This is why Ansible fits one-off fleet operations: nothing to install first.

7.Why is configuration management less central than it used to be?Medium

Two shifts. Containers moved configuration into the image: the Dockerfile installs the packages and the config is a ConfigMap, so there is no running VM to converge. And immutable infrastructure replaced patching in place: build a new image with Packer, roll new instances, throw the old ones away. Kubernetes then handles rollout, scaling and restarts. What remains for Ansible is the layer below containers, the node image, bastions, databases on VMs, on-prem hardware, plus one-off fleet operations. Puppet and Chef, which needed an agent on every host, mostly disappeared with that shift.

## Quiz

1.A task uses ansible.builtin.shell to run apt-get install nginx. What happens on the second run?

2.When does a handler run?

3.Which combination is the safe first step before a production run?

4.Which part of the stack is NOT Ansible's job?

5.What is the lowest precedence source of a variable?

## Practice these problems

* [OPSHigh load average and a process eating memory on a Linux hostMedium](/devops/problems/high-load-memory-leak-linux)
* [CODEBash: safe deploy script with locking, rollback and trapsMedium](/devops/problems/bash-safe-deploy-script)
* [CODETerraform: VPC and autoscaling group moduleMedium](/devops/problems/terraform-vpc-asg-module)

## Further reading

* [Ansible documentationGuidedocs.ansible.com](https://docs.ansible.com/)
* [Packer documentation: What is Packer?Guidedeveloper.hashicorp.com](https://developer.hashicorp.com/packer/docs/intro)
* [systemd System and Service ManagerGuidefreedesktop.org](https://www.freedesktop.org/wiki/Software/systemd/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousTerraform - infrastructure as code](/devops/learn/terraform-infrastructure-as-code)[NextKubernetes architecture and core objects](/devops/learn/kubernetes-architecture-core-objects)

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

1. [What is left for configuration management](#what-is-left-for-configuration-management)
2. [The model](#the-model)
3. [A complete playbook](#a-complete-playbook)
4. [Ansible next to Terraform and Packer](#ansible-next-to-terraform-and-packer)
5. [Common mistakes](#common-mistakes)
