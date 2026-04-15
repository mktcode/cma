# Content Management Agent

After 20+ years in web development, coding agents made me rethink the CMS. Can't we throw away the old paradigm of admin panels, databases, and complex workflows?
At least for smaller, more or less static websites?

I'm building a "content management agent" that edits simple HTML files, CSS and only the most basic JavaScript.
It uses a few general and a few site-specific skills (markdown instructions) and persists everything in a git repository.

The foundation is [Pi Coding Agent](https://pi.dev/).

## Setup

Use `init.yml` to set up the server. It will install nginx, certbot, and a few other packages.

