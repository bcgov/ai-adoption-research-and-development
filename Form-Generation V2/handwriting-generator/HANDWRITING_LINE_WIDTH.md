# What Controls “Words per Line” (Line Wrapping)

When you use **single-pass** mode for the `explain_changes` field, the full paragraph is sent to **handwritten.js** in one call. The library then wraps that text into multiple lines **inside its own code**. That’s why you see roughly 5 words per line even though we don’t split the text in our script.

## Where it’s controlled (handwritten.js)

In **handwritten.js** (npm package, source: `src/index.js`):

1. **`getBatchSize()`**  
   Returns a **random** value used as the wrap width (in **characters**):
   - Base: `10`
   - Plus 0–176 added with probability 1/8 each  
   - So you typically get about **10–35 characters per line** (often ~30), which is why you see ~5 words per line.

2. **`processText(rawText)`**  
   - Calls `getBatchSize()` to get that width.
   - Uses `wrapText(element, width)` to break each line at that character count (breaking at spaces when possible).

3. **Public API**  
   The library’s options are only: `outputType`, `inkColor`, `ruled`.  
   There is **no** `lineWidth` / `charsPerLine` / `width` option in the published API, so you cannot control wrap length from our code without changing the library.

So: **line length is controlled only inside handwritten.js by `getBatchSize()` and `wrapText(..., width)`.** Our script and worker do not control it unless we use a patched build that adds an option.

## How to get more words per line

### Option A: Patch handwritten.js to add a `lineWidth` option (recommended)

1. Fork [alias-rahil/handwritten.js](https://github.com/alias-rahil/handwritten.js) (or copy the repo).
2. In `src/index.js`:

   **a) Allow `lineWidth` in the options (Joi schema):**

   In `checkArgType`, extend the schema, e.g.:

   ```js
   lineWidth: Joi.number().integer().min(10).max(500).optional(),
   ```

   **b) Use it in `processText`:**

   - Change `processText` to accept an optional `lineWidth` (e.g. pass `optionalArgs.lineWidth` from `main`).
   - In `main`, when you have `optionalArgs.lineWidth`, pass it into `processText`.
   - In `processText`, instead of:

     ```js
     const batchSize = getBatchSize();
     // ...
     const width = maxLen > batchSize ? maxLen : batchSize;
     ```

     use something like:

     ```js
     const batchSize = typeof lineWidth === 'number' ? lineWidth : getBatchSize();
     const width = maxLen > batchSize ? maxLen : batchSize;
     ```

   (So when `lineWidth` is provided, use it as the wrap width; otherwise keep the current random behavior.)

3. Publish your fork (e.g. to npm or use as a git dependency) and point this project’s dependency to that build (e.g. in `import_map.json` or package resolution).

4. Our worker and batch API already pass through options (see below). So you can call the batch endpoint with `options: { lineWidth: 95 }` (or whatever value you want) and the patched library will use it.

### Option B: Use our option pass-through (after patching)

This repo already passes options through so a patched library can be used without code changes:

- **Batch API**: Request body can include optional `options`, e.g. `{ "texts": ["..."], "options": { "lineWidth": 95 } }`. The worker calls `handwritten(text, { outputType: 'png/b64', ...options })`.
- **Python**: `generate_handwriting_images_batch(texts, api_url, options=...)` sends `options` in the JSON body.
- **explain_changes**: In `build_test_form.py`, the single-pass batch call already passes `options={"lineWidth": 95}`. With the **stock** library this has no effect (option is ignored). Once you use a **patched** build that supports `lineWidth`, the same code will produce more words per line without further changes.

## Summary

| What                | Where                | Who controls it        |
|---------------------|----------------------|------------------------|
| Wrap width (chars)  | handwritten.js       | `getBatchSize()` + `wrapText(..., width)` |
| Words per line      | Same                 | Indirectly (width in chars) |
| Public API          | handwritten.js       | No `lineWidth` in stock package |

To get more words per line you need a **patched/forked** handwritten.js that accepts a `lineWidth` (or similar) option and uses it in `processText`. After that, our worker and API can pass `lineWidth` through as described above.
