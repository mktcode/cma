---
name: website-editing
description: How to edit a website and track changes. Use for incoming customer requests. ALWAYS!
---

# Website Editing

Websites are git repositories managed using **git worktrees**.

Each website has one central repository storage directory:

`/var/repos/DOMAIN`

Attached worktrees are used for deployment:

* Production worktree: `/var/www/html/DOMAIN/main`
* Staging worktree: `/var/www/html/DOMAIN/staging`

The production worktree has the `main` branch checked out.
The staging worktree has the persistent `staging` branch checked out.

The domain of a website serves the production worktree.
The staging domain (e.g. `staging.example.com`) serves the staging worktree.

DNS records are set up and point to the server, and nginx is configured to serve the correct directories for each domain.

Websites are static and consist of HTML, CSS, and JavaScript files. There is no database or server-side code.

The nginx configuration for the staging subdomain uses:

`add_header X-Robots-Tag "noindex, nofollow, noarchive";`

This prevents search engines from indexing the staging site.

The `robots.txt` file is not version controlled (`.gitignore`) but should stay the same on both staging and production most of the time. It should disallow all crawling on staging and allow crawling on production.

A website repo contains an `AGENTS.md` file at the repository root with specific instructions for that website. These instructions are authoritative and override any general instructions.

# Git Structure

Repositories should be initialized like this:

```bash
git clone REPOSITORY_URL /var/repos/DOMAIN
cd /var/repos/DOMAIN

git worktree add /var/www/html/DOMAIN/main main
git worktree add /var/www/html/DOMAIN/staging staging
```

Do NOT maintain separate cloned repositories for main/staging.
Do NOT clone one checkout from another.
Always use worktrees from the single central repository.

# Workflow

1. Read customer requests and understand what changes they want made to the website.
2. Read the repository's `AGENTS.md` file to understand any website-specific instructions.
3. Optional: Reply to the customer email in case of questions or to clarify the request. Stop. The customer's reply will trigger the next step automatically.
4. Update files in the staging worktree to implement the requested changes.
5. Commit changes directly to the `staging` branch and push to the `origin` remote repository.
6. Reply to the customer email with a link to the staging site and ask them to review the changes. Stop. The customer's reply will trigger the next step automatically.
7. If the customer requests revisions, continue editing the staging worktree and repeat review steps.
8. If the customer approves the changes:

   * Ensure local branches are up to date before merging or pushing if needed.
   * Ensure the production worktree is clean before deployment.
   * Merge `staging` into `main` from within the production worktree using a normal merge commit.
   * Push the updated `main` branch to the `origin` remote repository.
9. Reply to the customer email confirming that the changes are live.

# Important Rules

* The `staging` branch is persistent and always represents the latest preview/development state.
* The `main` branch always represents live production.
* Approved changes are merged from `staging` into `main`.
* Never reset or rewrite the `staging` branch unless explicitly instructed.
* Never edit the production worktree directly unless explicitly instructed.
* When asked to restore an earlier version of the website, do not move branch pointers backward.
* Do not deploy by checking out an old commit directly.
* Do not reset or rewrite history.
* Instead, use the previous version only as reference, restore the necessary file contents into the current staging worktree, and commit those changes as a new commit.
* All changes, including restorations, must be recorded as new forward-moving commits.
