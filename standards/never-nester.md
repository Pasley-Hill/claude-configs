# Never-Nester Standard

A coding philosophy focused on minimizing nesting depth to create immediately comprehensible code.

## Core Rule

**Maximum nesting depth: 3 levels**

- Level 1: Function/method body
- Level 2: One control structure (if, for, while)
- Level 3: One inner block

4+ levels is a code smell requiring immediate refactoring.

## Two Primary Techniques

### 1. Extraction - Decompose Complex Functions

Break down functions with nested loops or complex logic into smaller, single-responsibility functions.

- Extract inner loops into descriptive helper functions
- Pull out nested logic blocks into well-named functions
- Each function has exactly one clear, focused responsibility
- Name extracted functions to create self-documenting code

### 2. Inversion - Flatten Through Early Returns

Use guard clauses to handle edge cases first, letting the happy path flow naturally.

- Place validation and error checking at function tops
- Use early returns to exit immediately on failure conditions
- Invert if/else conditions to eliminate else blocks
- Convert nested if/else chains into sequential guard clauses

## Standard Code Structure

```
function example(params):
    # Gatekeeping section - declare all requirements upfront
    if not valid_condition_1:
        return error_or_none

    if not valid_condition_2:
        return error_or_none

    if not valid_condition_3:
        return error_or_none

    # Core functionality - happy path flows naturally
    result = do_main_work()
    return result
```

## Code Review Standards

- Flag any 4+ level nesting as requiring refactoring
- Suggest extraction for complex nested blocks
- Recommend inversion for if/else chains
- Propose descriptive function names that make code self-documenting
- Ensure error handling is declarative and visible at function tops
- Verify the happy path is unobstructed and easy to follow

## The Goal

Produce code where someone can mentally "discard" the error conditions at the top and immediately understand the core functionality flowing down the happy path. Every function should read like a clear, linear story of what it accomplishes.
