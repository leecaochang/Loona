import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Connection, subscribeEntities } from "home-assistant-js-websocket";

// Transport shim only. Connection dispatch and the entity store are stock HA.
class TestSocket extends EventTarget {
  OPEN = 1;
  readyState = 1;
  haVersion = "2026.9.4";
  sent = [];

  send(data) {
    this.sent.push(JSON.parse(data));
  }

  deliver(message) {
    this.dispatchEvent(new MessageEvent("message", { data: JSON.stringify(message) }));
  }

  close() {
    this.readyState = 3;
    this.dispatchEvent(new Event("close"));
  }
}

const steps = JSON.parse(readFileSync(0, "utf8"));
const socket = new TestSocket();
const connection = new Connection(socket, {
  setupRetry: 0,
  createSocket: async () => { throw new Error("Unexpected reconnect"); },
});
const warnings = [];
console.warn = (...args) => warnings.push(args.join(" "));
let current;
const unsubscribe = subscribeEntities(connection, (entities) => { current = entities; });
assert.deepEqual(socket.sent, [{ type: "subscribe_entities", id: 3 }]);
let acknowledgements = 0;
for (const step of steps) {
  for (const message of step.messages) {
    if (message.type === "result") acknowledgements++;
  }
  if (process.argv.includes("--coalesced")) socket.deliver(step.messages);
  else for (const message of step.messages) socket.deliver(message);
  await Promise.resolve();
  assert.deepEqual(
    Object.fromEntries(Object.entries(current).map(([id, entity]) => [id, entity.state])),
    step.expected,
    step.label,
  );
  assert.equal(connection.commands.has(3), true, step.label);
}
assert.equal(acknowledgements, 1, "Only the first bind acknowledges the subscription");
assert.deepEqual(warnings, [], "Retired generations must not update missing entities");
assert.equal(socket.sent.length, 1, "Scope updates must not reconnect or resubscribe");
unsubscribe();
connection.fireEvent("disconnected");
connection.close();
console.log(`${steps.length} checkpoints passed with the stock JS websocket collection`);
