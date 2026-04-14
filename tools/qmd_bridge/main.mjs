import { existsSync, mkdirSync } from "node:fs";
import { basename, dirname, extname, isAbsolute, resolve as resolvePath } from "node:path";

import { createStore } from "@tobilu/qmd";

const command = process.argv[2];

if (!command) {
  fail("Bridge command is required.");
}

const payload = await readJsonFromStdin();

try {
  let response;
  switch (command) {
    case "refresh":
      response = await handleRefresh(payload);
      break;
    case "search":
      response = await handleSearch(payload);
      break;
    default:
      fail(`Unsupported bridge command: ${command}`);
  }
  process.stdout.write(`${JSON.stringify(response)}\n`);
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}

async function handleRefresh(payload) {
  const dbPath = requireString(payload, "dbPath");
  const collectionName = requireString(payload, "collectionName");
  const collectionPath = requireString(payload, "collectionPath");
  const rootContext = requireString(payload, "rootContext");

  const store = await openStore(dbPath);
  try {
    await ensureCollection(store, { collectionName, collectionPath });
    await store.addContext(collectionName, "/", rootContext);
    const update = await store.update({ collections: [collectionName] });
    let embed = {
      docsProcessed: 0,
      chunksEmbedded: 0,
      errors: 0,
    };
    if (update.needsEmbedding > 0) {
      embed = await store.embed({});
    }
    return {
      collections: update.collections,
      indexed: update.indexed,
      updated: update.updated,
      unchanged: update.unchanged,
      removed: update.removed,
      needsEmbedding: update.needsEmbedding,
      docsProcessed: embed.docsProcessed,
      chunksEmbedded: embed.chunksEmbedded,
      embedErrors: embed.errors,
    };
  } finally {
    await store.close();
  }
}

async function handleSearch(payload) {
  const dbPath = requireString(payload, "dbPath");
  const collectionName = requireString(payload, "collectionName");
  const collectionPath = requireString(payload, "collectionPath");
  const query = requireString(payload, "query");
  const limit = requireInteger(payload, "limit");

  const store = await openStore(dbPath);
  try {
    const collections = await store.listCollections();
    if (!collections.some((collection) => collection.name === collectionName)) {
      throw new Error(
        `Scoped QMD collection \`${collectionName}\` is missing. Run \`rally memory refresh --run-id ...\` first.`
      );
    }
    const results = await store.search({
      query,
      collection: collectionName,
      limit,
      rerank: false,
    });
    return {
      results: results.map((result) => ({
        memoryId: basename(result.file, extname(result.file)),
        path: resolveResultPath(collectionPath, result.file),
        title: result.title || basename(result.file, extname(result.file)),
        snippet: cleanSnippet(result.bestChunk || result.body || result.title || result.file),
        score: result.score,
      })),
    };
  } finally {
    await store.close();
  }
}

async function openStore(dbPath) {
  mkdirSync(dirname(dbPath), { recursive: true });
  if (existsSync(dbPath)) {
    return createStore({ dbPath });
  }
  return createStore({
    dbPath,
    config: {
      collections: {},
    },
  });
}

async function ensureCollection(store, { collectionName, collectionPath }) {
  const pattern = "**/*.md";
  const collections = await store.listCollections();
  const existing = collections.find((collection) => collection.name === collectionName);
  if (existing && existing.pwd === collectionPath && existing.glob_pattern === pattern) {
    return;
  }
  if (existing) {
    await store.removeCollection(collectionName);
  }
  await store.addCollection(collectionName, { path: collectionPath, pattern });
}

function resolveResultPath(collectionPath, filePath) {
  if (isAbsolute(filePath)) {
    return filePath;
  }
  return resolvePath(collectionPath, filePath);
}

function cleanSnippet(text) {
  return text.trim().replace(/\s+/g, " ");
}

function requireString(payload, field) {
  const value = payload[field];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Bridge payload requires string field \`${field}\`.`);
  }
  return value.trim();
}

function requireInteger(payload, field) {
  const value = payload[field];
  if (!Number.isInteger(value)) {
    throw new Error(`Bridge payload requires integer field \`${field}\`.`);
  }
  return value;
}

async function readJsonFromStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const raw = chunks.join("").trim();
  if (raw === "") {
    return {};
  }
  try {
    const decoded = JSON.parse(raw);
    if (decoded === null || typeof decoded !== "object" || Array.isArray(decoded)) {
      throw new Error("Bridge payload must be a JSON object.");
    }
    return decoded;
  } catch (error) {
    throw new Error(
      error instanceof Error ? `Invalid bridge JSON payload: ${error.message}` : "Invalid bridge JSON payload."
    );
  }
}

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}
