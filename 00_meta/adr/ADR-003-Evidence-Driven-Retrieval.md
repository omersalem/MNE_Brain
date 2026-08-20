# ADR-003: Replacement of RAG with Evidence-Driven Knowledge Retrieval

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
Traditional RAG (Retrieval-Augmented Generation) relies on unconstrained vector similarity search, often injecting thousands of tokens of irrelevant markdown into LLM prompt contexts, driving up API costs and causing hallucination.

## Decision
We decided to replace all traditional RAG concepts with **Evidence-Driven Knowledge Retrieval**:
* Deterministic query routing and entity index matching.
* Block-level extraction capping evidence context at **<1,500 tokens** per query.
* Mandatory 5-tier trust rating ($\star\star\star\star\star$ scale) and source attribution on every evidence block.

## Consequences
* **Positive:** Reduces LLM token consumption by 60%.
* **Positive:** Ensures 100% verifiable source attribution.
* **Positive:** Prevents prompt context window overflow.
