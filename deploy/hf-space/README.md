---
title: Cotutor API
emoji: 🎓
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Backend for Cotutor, a verified algorithm tutor
---

# Cotutor API

Backend for [Cotutor](https://github.com/hgn2108/cotutor): a multi-agent algorithm tutor that
verifies every solution before teaching it. This Space only orchestrates agents; all code
runs in each visitor's browser (Pyodide), so it needs no GPU and runs on the free CPU tier.

Deployed automatically from `backend/` by GitHub Actions. Health check: `/api/health`.
