// Compile the pinned native HA card container with real Lit for browser tests.
import { build } from "esbuild";
const boundaries = `
export const ConditionalListenerMixin = (base) => class extends base { _conditionContext = {}; _conditionsVisible() { return true; } };
export const fireEvent = (node, type, detail) => node.dispatchEvent(new CustomEvent(type, {detail, bubbles:true, composed:true}));
export const computeCardSize = (node) => node.getCardSize();
export const computeRTLDirection = () => 'ltr';
export const migrateLayoutToGridOptions = (options) => options;
export const getConfigEntityId = (config) => config.entity;
export const checkConditionsMet = () => true;
export const tryCreateCardElement = (config) => window.loonaNativeFactory(config);
export const createErrorCardElement = () => document.createElement('div');
`;
await build({
  entryPoints: ["tests/startup_motion_browser.mjs"], outfile: process.argv[2],
  bundle: true, format: "esm", platform: "browser",
  alias: { "lit/decorators": "lit/decorators.js" },
  tsconfigRaw: { compilerOptions: { experimentalDecorators: true, useDefineForClassFields: false } },
  plugins: [{ name: "native-boundaries", setup(builder) {
    builder.onResolve({ filter: /^\.\.?\// }, (args) => /hui-card\.ts$/.test(args.importer)
      ? { path: args.path, namespace: "native" } : undefined);
    builder.onLoad({ filter: /.*/, namespace: "native" }, () => ({ contents: boundaries, loader: "js" }));
  } }],
});
