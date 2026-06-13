# Project Instructions

Your starter folder looks like the following structure:

```text
starter/
├── agentic/
│   ├── agents/
│   ├── design/
│   ├── tools/
│   └── workflow.py
├── data/
│   ├── core/
│   ├── external/
│   └── models/
├── .env
├── 01_external_db_setup.ipynb
├── 02_core_db_setup.ipynb
├── 03_agentic_app.ipynb
└── utils.py
```

---

# Design

Start by designing the solution. Your implementation will follow it.

Place all the documentation and diagrams about the design of your agentic system inside:

```text
agentic/design
```

---

# Setup

## External Database Setup

Run:

```text
01_external_db_setup.ipynb
```

This notebook contains all the data related to the account **Cultpass**, which is the first customer that has purchased **UDA-Hub**.

## Core Database Setup

Run:

```text
02_core_db_setup.ipynb
```

This notebook contains all the data related to the **UDA-Hub** application, including files received from Cultpass such as:

```text
cultpass_articles.jsonl
```

### Dataset Expansion Requirement

You need to expand **cultpass_articles** from **4 articles** to **at least 14 articles**.

Make sure the additional articles cover diverse topics that can support your agentic system.

---

# Agentic Workflow

## Agents and Tools

Develop your agents inside:

```text
agentic/agents
```

Develop your tools inside:

```text
agentic/tools
```

This will help maintain modularity and separation of concerns.

---

## Workflow Orchestration

Develop your workflow orchestration inside:

```text
workflow.py
```

There is already a sample implementation provided.

**Do not use it.**

Create the graph entirely from scratch and do **not** use the prebuilt workflow.

---

## Database Tooling

When developing tools that abstract database operations for either:

- Retrieval
- Actions

be mindful of relative and absolute paths.

It is strongly recommended to use something similar to **MCP servers** for tool implementations.

---

## RAG Documentation

If you use **Retrieval-Augmented Generation (RAG)** for retrieval:

- Document the retrieval architecture.
- Explain how documents are indexed.
- Explain how retrieval works.
- Explain how retrieved context is incorporated into agent decisions.

---

## Memory Requirements

### Short-Term Memory

For session-level memory, you can use:

```python
thread_id
```

### Long-Term Memory

You are free to implement long-term memory using:

- Semantic search
- Vector databases
- Embedding-based retrieval
- Other suitable approaches

---

# Run

A helper function already exists inside:

```text
utils.py
```

```python
chat_interface()
```

This is currently implemented as a simple:

```python
while True:
    ...
```

loop.

Feel free to improve it.

---

## Application Entry Point

You are **not required** to use:

```text
03_agentic_app.ipynb
```

You may instead develop the application as a Python module.

If so, name it:

```text
03_agentic_app.py
```

and clearly document how to run the project.

---

## Testing

You **must create test cases** for the project.

Your implementation should include tests that validate:

- Agent routing
- Classification accuracy
- Tool execution
- Memory retrieval
- Escalation logic
- End-to-end workflow execution

---

# Submission Instructions

You are receiving starter code, but your submission must contain all artifacts under:

```text
solution/
```

The evaluation team will **not** inspect:

```text
starter/
```

If you reuse starter code, make sure it is copied into:

```text
solution/
```

before submission.

---

## Environment Documentation

If you install any packages:

- Include package names and versions in the documentation.
- Provide a `requirements.txt` file.
- Provide the Python version used for development (if developing locally).

---

# DON'Ts

### Do Not

❌ Import or reference folders outside:

```text
solution/
```

❌ Share your:

```text
.env
```

file

❌ Submit large:

```text
.db
```

files

❌ Submit only the notebooks without the accompanying project artifacts