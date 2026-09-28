const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const panelSource = fs.readFileSync("ui/panel.js", "utf8");

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  toggle(name, force) {
    if (force === undefined) {
      if (this.values.has(name)) {
        this.values.delete(name);
        return false;
      }
      this.values.add(name);
      return true;
    }

    if (force) {
      this.values.add(name);
    } else {
      this.values.delete(name);
    }
    return !!force;
  }

  contains(name) {
    return this.values.has(name);
  }
}

class FakeElement {
  constructor(id) {
    this.id = id || null;
    this.textContent = "";
    this.innerHTML = "";
    this.hidden = false;
    this.disabled = false;
    this.dataset = {};
    this.style = {};
    this.className = "";
    this.classList = new FakeClassList();
    this.children = [];
    this.listeners = {};
  }

  addEventListener(type, fn) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(fn);
  }

  trigger(type, event) {
    const listeners = this.listeners[type] || [];
    for (const listener of listeners) {
      listener(event || { target: this });
    }
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }
}

class FakeDocument {
  constructor() {
    this.body = new FakeElement("body");
    this.listeners = {};
    this.elements = {};
    for (const id of [
      "status",
      "comp-meta",
      "timeline",
      "selection",
      "editor",
      "diagnostics",
      "diagnostics-text",
      "diagnostics-toggle",
      "refresh"
    ]) {
      this.elements[id] = new FakeElement(id);
    }
    this.elements.diagnostics.hidden = true;
  }

  getElementById(id) {
    return this.elements[id];
  }

  querySelectorAll(selector) {
    if (selector === "button") {
      return [
        this.elements["diagnostics-toggle"],
        this.elements.refresh
      ];
    }
    return [];
  }

  addEventListener(type, fn) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(fn);
  }

  trigger(type) {
    for (const fn of this.listeners[type] || []) {
      fn();
    }
  }

  createElement() {
    return new FakeElement();
  }

  createDocumentFragment() {
    return new FakeElement("fragment");
  }
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function flush() {
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
}

function buildInfo(id, commit) {
  return {
    buildId: id,
    version: "0.0.1",
    gitCommit: commit,
    gitState: "clean",
    artifactType: "cep-extension"
  };
}

function createHarness(options) {
  options = options || {};
  const document = new FakeDocument();
  const browserInfo = options.browserInfo || buildInfo("build-a", "a".repeat(40));
  const hostInfo = options.hostInfo === undefined
    ? browserInfo
    : options.hostInfo;

  let snapshotCalls = 0;
  let buildInfoCalls = 0;
  let snapshotFactory = options.snapshotFactory || (() => Promise.resolve(null));

  const adapter = {
    getBuildInfo() {
      buildInfoCalls += 1;
      if (options.buildInfoError) {
        return Promise.reject(options.buildInfoError);
      }
      return Promise.resolve(hostInfo);
    },
    getSnapshot() {
      snapshotCalls += 1;
      return snapshotFactory();
    },
    selectLayer() {
      return Promise.reject(new Error("not used"));
    },
    moveLayerFrames() {
      return Promise.reject(new Error("not used"));
    },
    trimLayerInFrames() {
      return Promise.reject(new Error("not used"));
    },
    trimLayerOutFrames() {
      return Promise.reject(new Error("not used"));
    }
  };

  const loggedErrors = [];
  const context = vm.createContext({
    window: {
      FSTRLineBuildInfo: browserInfo,
      FSTRLineCEPAdapter: adapter,
      FSTRLineCore: {}
    },
    document,
    console: {
      log() {},
      error(...args) {
        loggedErrors.push(args);
      }
    },
    Promise,
    Error,
    String,
    Number,
    Math,
    setTimeout,
    clearTimeout
  });

  vm.runInContext(panelSource, context, { filename: "ui/panel.js" });
  document.trigger("DOMContentLoaded");

  return {
    document,
    adapter,
    loggedErrors,
    get snapshotCalls() {
      return snapshotCalls;
    },
    get buildInfoCalls() {
      return buildInfoCalls;
    },
    setSnapshotFactory(factory) {
      snapshotFactory = factory;
    }
  };
}

test("first load with matching Build Identity and no comp stays non-error", async () => {
  const harness = createHarness();
  await flush();

  assert.equal(harness.buildInfoCalls, 1);
  assert.equal(harness.snapshotCalls, 1);
  assert.match(
    harness.document.elements["diagnostics-text"].textContent,
    /Identity match: YES/
  );
  assert.equal(
    harness.document.elements.status.textContent,
    "Open a composition in After Effects."
  );
  assert.equal(
    harness.document.elements.status.classList.contains("is-error"),
    false
  );
  assert.equal(harness.document.elements.editor.hidden, true);
});

test("Build Identity mismatch remains visible even with no active comp", async () => {
  const harness = createHarness({
    hostInfo: buildInfo("build-b", "b".repeat(40))
  });
  await flush();

  assert.match(
    harness.document.elements["diagnostics-text"].textContent,
    /Identity match: NO/
  );
  assert.equal(
    harness.document.elements.status.textContent,
    "Build Identity mismatch — open Diagnostics."
  );
  assert.equal(
    harness.document.elements.status.classList.contains("is-error"),
    true
  );
});

test("Build Identity bridge failure remains visible after empty refresh", async () => {
  const harness = createHarness({
    buildInfoError: new Error("identity bridge unavailable")
  });
  await flush();

  assert.match(
    harness.document.elements["diagnostics-text"].textContent,
    /Identity match: NO/
  );
  assert.equal(
    harness.document.elements.status.textContent,
    "Build Identity mismatch — open Diagnostics."
  );
  assert.equal(harness.loggedErrors.length > 0, true);
});

test("Diagnostics button toggles panel visibility", async () => {
  const harness = createHarness();
  await flush();

  const diagnostics = harness.document.elements.diagnostics;
  const button = harness.document.elements["diagnostics-toggle"];

  assert.equal(diagnostics.hidden, true);
  button.trigger("click");
  assert.equal(diagnostics.hidden, false);
  button.trigger("click");
  assert.equal(diagnostics.hidden, true);
});

test("busy refresh suppresses accidental double host call and restores controls", async () => {
  const harness = createHarness();
  await flush();

  const pending = deferred();
  const before = harness.snapshotCalls;
  harness.setSnapshotFactory(() => pending.promise);

  const refresh = harness.document.elements.refresh;
  refresh.trigger("click");
  refresh.trigger("click");

  assert.equal(harness.snapshotCalls, before + 1);
  assert.equal(refresh.disabled, true);
  assert.equal(harness.document.body.classList.contains("is-busy"), true);

  pending.resolve(null);
  await flush();

  assert.equal(refresh.disabled, false);
  assert.equal(harness.document.body.classList.contains("is-busy"), false);
});
