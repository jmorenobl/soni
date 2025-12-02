# Design Documentation Archive

This directory contains **historical design documents** that show the evolution of thinking during the Soni Framework redesign. These documents are preserved for context and reference but are **not part of the final design**.

## ⚠️ Important Notice

**Do not implement designs from this archive.** These documents represent:
- Problem analysis and investigations
- Superseded design approaches
- Evolution of design thinking
- Consolidation process documentation

For the **final design**, see the main [design/](../) directory, specifically [20-consolidated-design-decisions.md](../20-consolidated-design-decisions.md).

## 📂 Archive Contents

### Consolidation Process
- **00-CONSOLIDATION-SUMMARY.md** - Summary of the consolidation effort that resolved contradictions across documents 00-19

### Quick References (Superseded)
- **00-quick-reference.md** - Early quick reference (superseded by doc 20)
- **QUICK-DECISION-INDEX.md** - Early decision index (superseded by doc 20's lookup table)

### Problem Analysis
- **15-current-problems-analysis.md** - Analysis of structural problems in the original implementation
  - Provides context for why the redesign was needed
  - Root cause analysis
  - Performance measurements

### Design Investigations
- **16-start-prefix-investigation.md** - Investigation of "start_" prefix issue
  - **Decision**: REMOVE the prefix
  - Analysis of why it existed and why it's problematic

- **17-state-validation-approach.md** - Analysis of state machine libraries
  - **Decision**: Do NOT use `transitions` library with LangGraph
  - Recommends lightweight custom validation instead

### Superseded Designs
- **18-hybrid-slot-collection-strategy.md** - 3-tier slot collection approach
  - **Status**: SUPERSEDED by document 19
  - **Why superseded**: Pattern extraction tier was too simplistic for realistic user behavior
  - **Replaced by**: 2-level DSPy-based approach (doc 19)

## 🔍 Why Keep These Documents?

These documents are preserved because they:
1. **Show the evolution** - Demonstrate how the design matured through analysis
2. **Provide context** - Explain why certain approaches were rejected
3. **Document decisions** - Record what was considered and why
4. **Help onboarding** - New team members can understand the reasoning process

## 📖 How to Use This Archive

### For Understanding "Why?"
If you're wondering why a specific design decision was made:
1. Check the main [20-consolidated-design-decisions.md](../20-consolidated-design-decisions.md) first
2. Look in this archive for the detailed investigation documents (16, 17)
3. Read the problem analysis (15) for root causes

### For Historical Context
To understand the evolution of a specific feature:
1. Read problem analysis (15) - What was wrong
2. Read investigations (16, 17) - What was analyzed
3. Read superseded designs (18) - What was tried
4. Read final design (19, 20) - What was chosen

### Example: Slot Collection Evolution
```
Problem (15) → Investigation → Superseded Design (18) → Final Design (19) → Consolidated (20)
```

## ⚠️ Common Pitfalls

### Do NOT:
- ❌ Implement designs from this archive
- ❌ Mix archived approaches with final design
- ❌ Assume older documents are still valid
- ❌ Reference these documents in implementation code

### DO:
- ✅ Use for understanding design rationale
- ✅ Reference in discussions about "why not X?"
- ✅ Learn from the evolution process
- ✅ Cite when explaining decisions to new team members

## 📊 Document Status Legend

All documents in this archive are marked with one of these statuses:

| Status | Meaning |
|--------|---------|
| ⚠️ SUPERSEDED | Replaced by a newer design - do not implement |
| 📋 HISTORICAL | Problem analysis or investigation - for context only |
| 🔄 PROCESS | Documentation about the design process itself |

## 🔗 See Final Design

For the current, final design that should be implemented:
- **Main Design Directory**: [../](../)
- **Single Source of Truth**: [20-consolidated-design-decisions.md](../20-consolidated-design-decisions.md)
- **Implementation Roadmap**: [14-implementation-roadmap.md](../14-implementation-roadmap.md)

## 📝 Version History

- **2025-12-02**: Archive created during documentation cleanup
  - Moved 7 historical/superseded documents from main design/ directory
  - Created this README to explain archive purpose
  - Ensures confusion-free final design documentation

---

**Archive Purpose**: Preserve design evolution for context, not for implementation
**Status**: Historical reference only
**Last Updated**: 2025-12-02
