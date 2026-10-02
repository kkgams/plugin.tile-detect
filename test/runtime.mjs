import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const spec = JSON.parse(readFileSync('component.json', 'utf8'));
for (const artifact of spec.artifacts) {
  const m = await import(`../build/jco/${artifact}/component.js`);
  if (spec.slug === 'pack') {
    const result = m.pack.pack({width: 8, height: 8, padding: 1, autoSize: false,
      rects: [{id: undefined, width: 3, height: 2}, {id: 9, width: 2, height: 2}, {id: undefined, width: 10, height: 1}]});
    assert.equal(result.packedCount, 2);
    assert.equal(result.failedCount, 1);
    assert.equal(result.rects[1].id, 9);
    assert.throws(() => m.pack.pack({width: 0, height: 4, padding: 0, autoSize: false, rects: []}));
  } else if (spec.slug === 'random') {
    m.seededRandom.setSeed(123n);
    const a = m.random.getRandomBytes(16n);
    m.seededRandom.setSeed(123n);
    const b = m.random.getRandomBytes(16n);
    assert.deepEqual(a, b);
    assert.equal(a.length, 16);
    assert.equal(m.seededRandom.getSeed(), 123n);
  } else if (spec.slug === 'sql') {
    const connection = m.types.Connection.open(':memory:');
    const statement = m.types.Statement.prepare('SELECT 42 AS answer', []);
    const rows = m.readwrite.query(connection, statement);
    assert.equal(rows[0].fieldName, 'answer');
    assert.equal(Number(rows[0].value.val), 42);
    if (artifact === 'plugin.sql-vec.wasm') {
      const vec = m.types.Statement.prepare('SELECT vec_version() AS version', []);
      assert.match(m.readwrite.query(connection, vec)[0].value.val, /^v?\d+\.\d+/);
    }
  } else throw new Error('Unimplemented runtime test');
}
console.log('Standalone jco WASM runtime assertions passed');
