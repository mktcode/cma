---
name: website-editing
description: How to edit a website and track changes. Use for incoming customer requests. ALWAYS!
---

# Website Editing

Websites are git repositories.

Websites live in `/var/www/html/DOMAIN/main` and `/var/www/html/DOMAIN/staging`. Both directories have the same repository checked out, but the staging directory has the `staging` branch checked out, while the main directory has the `main` branch checked out.

The staging directory is connected to a remote repository to push changes to.
The main directory is cloned from the staging directory as its origin.

The domain of a website serves the `main` directory, while the staging domain (e.g. `staging.example.com`) serves the `staging` directory.
DNS records are set up and point to the server, and nginx is configured to serve the correct directories for each domain.

Websites are static and consist of HTML, CSS, and JavaScript files. There is no database or server-side code.
But each website is a git repository, and the agent can use git to manage changes, create branches, and merge changes from staging to live.

The nginx configuration for the staging subdomain uses `add_header X-Robots-Tag "noindex, nofollow, noarchive";` to prevent search engines from indexing the staging site.
The robots.txt is not version controlled (`.gitignore`) but should stay the same in both directories most of the time.

A website repo contains an `AGENTS.md` file with instructions for the agent on how to edit the website. These instructions are authoritative and override any general instructions.

# Workflow

1. Read customer rquests and understand what changes they want to make to the website.
2. Read the `AGENTS.md` file in the website repo to understand any specific instructions for this website.
3. Optional: Reply to the customer email in case of questions or to clarify the request. Stop. The customer's reply will trigger the next step automatically.
4. Update the files in the staging directory to implement the requested changes. Commit the changes to the `staging` branch and push to the remote repository.
5. Reply to the customer email with a link to the staging site and ask them to review the changes. Stop. The customer's reply will trigger the next step automatically.
6. If the customer approves the changes, merge the `staging` branch into the `main` branch and push the changes to the remote repository.