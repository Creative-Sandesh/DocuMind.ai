import assert from "node:assert/strict";
import test from "node:test";
import { serverBaseUrl } from "../src/services/config.ts";
import { wavFromSamples } from "../src/utils/wav.ts";

test("LAN API defaults to same-origin paths and normalizes an override", () => {
  assert.equal(serverBaseUrl(), "");
  assert.equal(`${serverBaseUrl()}/api/student/login`, "/api/student/login");
  assert.equal(serverBaseUrl("https://192.168.1.25:8443/"), "https://192.168.1.25:8443");
});

test("microphone samples become valid mono 16 kHz PCM WAV", async () => {
  const wav = wavFromSamples([new Float32Array([0, 0.5]), new Float32Array([-0.5, 1])], 16000);
  assert.equal(wav.type, "audio/wav");
  const bytes = await wav.arrayBuffer();
  const view = new DataView(bytes);
  const text = (start, count) => String.fromCharCode(...new Uint8Array(bytes, start, count));
  assert.equal(text(0, 4), "RIFF");
  assert.equal(text(8, 4), "WAVE");
  assert.equal(view.getUint16(22, true), 1);
  assert.equal(view.getUint32(24, true), 16000);
  assert.equal(view.getUint16(34, true), 16);
  assert.equal(view.getUint32(40, true), 8);
  assert.equal(view.getInt16(44, true), 0);
  assert.equal(view.getInt16(46, true), 16383);
  assert.equal(view.getInt16(48, true), -16384);
  assert.equal(view.getInt16(50, true), 32767);
});

test("48 kHz capture is resampled to 16 kHz with the expected duration", async () => {
  const wav = wavFromSamples([new Float32Array(48000)], 48000);
  const view = new DataView(await wav.arrayBuffer());
  assert.equal(view.getUint32(40, true), 16000 * 2);
  assert.equal(view.byteLength, 44 + 16000 * 2);
});
