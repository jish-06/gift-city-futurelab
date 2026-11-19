# Publish this folder to GitHub

1. Unzip `fxnexus-mvp-github-ready.zip`.
2. Open a terminal in the extracted `fxnexus-mvp` folder.
3. Initialise and commit:

```bash
git init
git add .
git status  # verify no .env or real credentials are staged
git commit -m "Build FXNexus event-driven treasury MVP"
```

4. Create an empty repository on GitHub (do not initialise it with a README if you already have this one).
5. Add the remote and push, replacing the URL with your repository URL:

```bash
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/fxnexus-mvp.git
git push -u origin main
```

Never commit `backend/.env`, API tokens, database passwords, or customer data. Keep only `.env.example` files in the repository.
