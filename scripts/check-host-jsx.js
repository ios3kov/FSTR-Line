const fs = require("node:fs");
const vm = require("node:vm");

const source = fs
  .readFileSync("host/cep/host.jsx", "utf8")
  .replace(/^#include[^\n]*$/gm, "");

new vm.Script(source, { filename: "host/cep/host.jsx" });
console.log("host/cep/host.jsx syntax OK");
