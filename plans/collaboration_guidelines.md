# Collaboration & Learning Guidelines

These guidelines define how the AI assistant and the user collaborate on the **Departmental Knowledge Assistant** codebase.

---

## 1. Terminal Commands & Virtual Environment Execution
- **User Executes Commands:** Do NOT run commands (such as starting services, installing dependencies, database migrations, running scripts, or compiling models) automatically.
- **Provide Command Blocks:** Always provide the exact shell commands in clear markdown code blocks with instructions (e.g. activating `.venv`, setting environment variables) so the user can review and execute them in their terminal.
- **Explain What the Command Does:** Explain why the command is being run and what flags/options mean, especially concerning Python virtual environments (`.venv`).

---

## 2. Library Documentation & Concepts
- Whenever introducing or writing code with specific libraries, explicitly list the libraries used and provide:
  - What the library does.
  - Why we chose it for this specific architecture.
  - Links or concepts to read up on (e.g., PyJWT, passlib, asyncpg, pgvector).

---

## 3. Interactive Sandbox Coding & Questions
- **Pair-Programming Mode:** Encourage hands-on learning.
- **Ask Checkpoint Questions & Provide Challenges:**
  - Before or after creating key architectural modules, pause and present short conceptual or implementation questions.
  - Offer optional "sandbox challenges" where the user can write or fill in part of a function, schema, or test themselves.

