# Parallel Form Generation - Control Guide

## Overview

The form generation script now supports parallel generation of multiple forms for significantly faster performance. This document explains how to control the parallelism.

## How It Works

When generating multiple forms (e.g., `python build_test_form.py 5`), the script can generate them concurrently instead of sequentially:

**Sequential** (old way):
```
Form 0: [████████████] 10s
Form 1:                  [████████████] 10s
Form 2:                                    [████████████] 10s
Total: 30s
```

**Parallel** (new way, 3 workers):
```
Form 0: [████████████] 10s
Form 1: [████████████] 10s (parallel)
Form 2: [████████████] 10s (parallel)
Total: 10s (3× faster!)
```

## Controlling Parallelism

### Environment Variable: `MAX_PARALLEL_FORMS`

Control how many forms are generated concurrently using the `MAX_PARALLEL_FORMS` environment variable.

**Default**: 4 workers

**Examples**:

```bash
# Default (4 workers)
python build_test_form.py 10

# Disable parallelism (sequential)
MAX_PARALLEL_FORMS=1 python build_test_form.py 10

# Conservative (2 workers)
MAX_PARALLEL_FORMS=2 python build_test_form.py 10

# Aggressive (8 workers)
MAX_PARALLEL_FORMS=8 python build_test_form.py 20

# Match number of forms (if generating 3 forms, use 3 workers)
MAX_PARALLEL_FORMS=3 python build_test_form.py 3
```

### How It's Determined

The actual number of parallel workers is:
```python
max_workers = min(num_loops, MAX_PARALLEL_FORMS)
```

This means:
- If generating 3 forms with `MAX_PARALLEL_FORMS=10`, only 3 workers are used
- If generating 10 forms with `MAX_PARALLEL_FORMS=4`, only 4 workers are used
- Single form generation always uses 1 worker (no parallelism needed)

## Performance Guide

### Recommended Settings

| Forms to Generate | Recommended MAX_PARALLEL_FORMS | Expected Time |
|-------------------|-------------------------------|--------------|
| 1                 | 1 (default)                   | ~10s         |
| 2-3               | 2-3                           | ~10-12s      |
| 4-10              | 4 (default)                   | ~10-15s per batch |
| 10-20             | 4-5                           | ~15-20s per batch |
| 20+               | 4-6                           | ~20-25s per batch |

### Why Not More Workers?

- **Service capacity**: The Node server processes batch requests sequentially
- **Resource Limits**: Too many concurrent requests can cause:
  - Memory pressure (each form uses ~110MB)
  - CPU saturation
  - Request queuing (diminishing returns)

**Sweet Spot**: 3-4 parallel forms provides excellent speedup without overloading the system.

## Examples

### Generate 5 Forms (Default Parallelism)
```bash
python build_test_form.py 5
# Uses 4 workers (default)
# Expected: ~15-20s total
```

### Generate 10 Forms Sequentially
```bash
MAX_PARALLEL_FORMS=1 python build_test_form.py 10
# Uses 1 worker (sequential)
# Expected: ~95s total
```

### Generate 20 Forms with Aggressive Parallelism
```bash
MAX_PARALLEL_FORMS=6 python build_test_form.py 20
# Uses 6 workers
# Expected: ~35-45s total
```

### Generate 3 Forms with Matching Parallelism
```bash
MAX_PARALLEL_FORMS=3 python build_test_form.py 3
# Uses 3 workers (matches number of forms)
# Expected: ~10-12s total
```

## Performance Comparison

Based on testing:

| Forms | Sequential | Parallel (4 workers) | Speedup |
|-------|------------|---------------------|---------|
| 1     | ~10s       | ~10s                | 1×      |
| 3     | ~30s       | ~10-12s             | 2.5-3×  |
| 5     | ~50s       | ~15-18s             | 2.8-3.3×|
| 10    | ~100s      | ~25-35s             | 2.9-4×  |

## Troubleshooting

### Forms Taking Longer Than Expected

**Symptom**: Parallel generation is slower than expected

**Possible Causes**:
1. **Too many workers**: Handwriting service is overloaded
   - **Solution**: Reduce `MAX_PARALLEL_FORMS` to 3-4

2. **System resource limits**: CPU or memory constrained
   - **Solution**: Reduce `MAX_PARALLEL_FORMS` to 2-3

3. **Network issues**: HTTP requests timing out
   - **Solution**: Check the handwriting service is running and responsive

### Memory Issues

**Symptom**: Out of memory errors

**Solution**: Reduce `MAX_PARALLEL_FORMS`
- Each form uses ~110MB
- 4 forms = ~440MB
- 10 forms = ~1.1GB

### Want Sequential Generation

**Solution**: Set `MAX_PARALLEL_FORMS=1`
```bash
MAX_PARALLEL_FORMS=1 python build_test_form.py 10
```

## Technical Details

### Implementation

- Uses Python's `concurrent.futures.ThreadPoolExecutor`
- Thread-safe: Each form generation is independent
- No shared mutable state between forms
- Each form writes to unique output files

### Thread Safety

✅ **Safe to parallelize**:
- Form data generation (independent)
- Batch API calls (independent HTTP requests)
- Image processing (independent PIL operations)
- File I/O (unique filenames)

✅ **No conflicts**:
- Template loading (read-only)
- Output files (unique per form)
- Global session (thread-safe)

## Advanced Usage

### Setting Default Parallelism

To change the default without setting environment variable each time, modify `build_test_form.py`:

```python
# Line ~260
max_parallel = int(os.environ.get('MAX_PARALLEL_FORMS', '4'))  # Change '4' to your default
```

### Monitoring Performance

The script outputs timing information:
```
[Overall] Parallelism: 4 worker(s)
[Overall] Completed 1/10 forms
[Overall] Completed 2/10 forms
...
[Overall] Generated 10 form(s) in 25.123s (avg: 2.512s per form)
```

Watch for:
- **Average time per form**: Should be similar to single form time when parallelized
- **Completion rate**: Forms should complete steadily, not all at once
- **Total time**: Should be much less than sequential (forms × single_form_time)
