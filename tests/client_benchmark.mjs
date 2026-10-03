import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { performance } from "node:perf_hooks";
import { Connection, subscribeEntities } from "home-assistant-js-websocket";

// Only the transport is simulated. JSON decoding and collection updates are stock.
class ReplaySocket extends EventTarget {
  OPEN = 1;
  readyState = 1;
  haVersion = "2026.9.4";
  sent = [];

  send(data) { this.sent.push(JSON.parse(data)); }
  deliver(data) { this.dispatchEvent(new MessageEvent("message", { data })); }
  close() { this.readyState = 3; }
}

const { cases, samples } = JSON.parse(readFileSync(0, "utf8"));
const median = (values) => {
  values.sort((a, b) => a - b);
  const middle = Math.floor(values.length / 2);
  return values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
};
const result = { node: process.version, cases: {} };
const warnings = [];
console.warn = (...args) => warnings.push(args.join(" "));
for (const [label, packets] of Object.entries(cases)) {
  const initial = [], updates = [];
  for (let sample = 0; sample <= samples; sample++) {
    const socket = new ReplaySocket();
    const connection = new Connection(socket, {
      setupRetry: 0,
      createSocket: async () => { throw new Error("Unexpected reconnect"); },
    });
    const subscriptionId = JSON.parse(packets.initial.find(packet => JSON.parse(packet).type === "event")).id;
    connection.commandId = subscriptionId - 1;
    let current;
    const stop = subscribeEntities(connection, (states) => { current = states; });
    assert.deepEqual(socket.sent, [{ type: "subscribe_entities", id: subscriptionId }]);
    let started = performance.now();
    for (const packet of packets.initial) socket.deliver(packet);
    const initialMs = performance.now() - started;
    await Promise.resolve();
    assert.equal(Object.keys(current).length, packets.expected_count);
    started = performance.now();
    for (const packet of packets.updates) socket.deliver(packet);
    const updatesMs = performance.now() - started;
    if (packets.expected_states) {
      for (const [entityId, state] of Object.entries(packets.expected_states)) {
        assert.equal(current[entityId]?.state, state);
      }
    } else {
      assert.equal(Object.values(current).filter((state) => state.state === "1").length, packets.expected_changes);
    }
    assert.deepEqual(warnings, []);
    if (sample) { initial.push(initialMs); updates.push(updatesMs); }
    stop();
    connection.fireEvent("disconnected");
    connection.close();
  }
  result.cases[label] = {
    snapshot_median_ms: median(initial),
    updates_median_ms: median(updates),
  };
}
console.log(JSON.stringify(result));
