module.exports = [
"[turbopack-node]/transforms/postcss.ts?config=[project]/frontend/postcss.config.mjs { CONFIG => \"[project]/frontend/postcss.config.mjs [postcss] (ecmascript)\" } [postcss] (ecmascript, async loader)", ((__turbopack_context__) => {

__turbopack_context__.v((parentImport) => {
    return Promise.all([
  "chunks/19xk_071lcl-._.js",
  "chunks/[root-of-the-server]__21aj5cg._.js"
].map((chunk) => __turbopack_context__.l(chunk))).then(() => {
        return parentImport("[turbopack-node]/transforms/postcss.ts?config=[project]/frontend/postcss.config.mjs { CONFIG => \"[project]/frontend/postcss.config.mjs [postcss] (ecmascript)\" } [postcss] (ecmascript)");
    });
});
}),
];