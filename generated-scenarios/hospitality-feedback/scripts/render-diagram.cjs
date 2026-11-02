"use strict";
const fs = require("node:fs");
const { Resvg } = require("../.tools/render/node_modules/@resvg/resvg-js");
const source = fs.readFileSync(process.argv[2]);
const image = new Resvg(source, {
  font: { loadSystemFonts: true, defaultFontFamily: "Segoe UI" },
  background: "white"
});
fs.writeFileSync(process.argv[3], image.render().asPng());
