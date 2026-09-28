const fs = require("node:fs");
const vm = require("node:vm");

const source = fs
  .readFileSync("tests/ae/runtime-smoke.jsx", "utf8")
  .replace(/^#include[^\n]*$/gm, "");

new vm.Script(source, { filename: "tests/ae/runtime-smoke.jsx" });
console.log("tests/ae/runtime-smoke.jsx syntax OK");
