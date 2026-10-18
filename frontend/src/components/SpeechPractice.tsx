import { useEffect, useRef, useState } from "react";
import { speakText, transcribeAudio } from "../services/studentApi";
import type { SpeechStatus, Transcription } from "../types/student";
import { wavFromSamples } from "../utils/wav";

type Capture = { context: AudioContext; stream: MediaStream; source: MediaStreamAudioSourceNode; processor: ScriptProcessorNode; gain: GainNode; chunks: Float32Array[]; timer: number };

export default function SpeechPractice({ token, status, text, onTextChange }: { token: string; status: SpeechStatus | null; text: string; onTextChange: (text: string) => void }) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Transcription | null>(null);
  const [error, setError] = useState("");
  const capture = useRef<Capture | null>(null);
  useEffect(() => () => {
    const current = capture.current;
    if (!current) return;
    window.clearTimeout(current.timer); current.stream.getTracks().forEach((track) => track.stop());
    current.source.disconnect(); current.processor.disconnect(); current.gain.disconnect();
    void current.context.close(); capture.current = null;
  }, []);

  async function listen() {
    setError("");
    try { await speakText(token, text.trim()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to play local speech."); }
  }

  async function transcribe(audio: Blob) {
    setBusy(true); setError(""); setResult(null);
    try { setResult(await transcribeAudio(token, audio)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to transcribe audio."); }
    finally { setBusy(false); }
  }

  async function stop() {
    const current = capture.current;
    if (!current) return;
    capture.current = null; window.clearTimeout(current.timer);
    current.stream.getTracks().forEach((track) => track.stop());
    current.source.disconnect(); current.processor.disconnect(); current.gain.disconnect();
    await current.context.close(); setRecording(false);
    if (current.chunks.length) await transcribe(wavFromSamples(current.chunks, current.context.sampleRate));
  }

  async function start() {
    if (!status?.speech_to_text || capture.current) return;
    setError(""); setResult(null);
    let stream: MediaStream | undefined;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const gain = context.createGain(); gain.gain.value = 0;
      const chunks: Float32Array[] = [];
      processor.onaudioprocess = (event) => chunks.push(event.inputBuffer.getChannelData(0).slice());
      source.connect(processor); processor.connect(gain); gain.connect(context.destination);
      const timer = window.setTimeout(() => { void stop(); }, 15000);
      capture.current = { context, stream, source, processor, gain, chunks, timer };
      setRecording(true);
    } catch (cause) { stream?.getTracks().forEach((track) => track.stop()); setError(cause instanceof Error ? cause.message : "Microphone access failed."); }
  }

  return <section className="learning-result speech-practice" aria-label="Offline speech practice">
    <div className="learning-result-heading"><div><span className="learning-eyebrow">Optional local audio</span><h3>Listen and repeat</h3></div><span>{status?.language ?? "Checking"}</span></div>
    <p>{status?.message ?? "Checking local speech engines..."} Speech is processed by the local backend.</p>
    <label htmlFor="speech-target">Word or phrase to practice</label>
    <input id="speech-target" value={text} maxLength={500} onChange={(event) => { onTextChange(event.target.value); setResult(null); }} placeholder="Enter a word or phrase" />
    <div className="review-ratings">
      <button type="button" className="secondary-button" disabled={!status?.text_to_speech || !text.trim()} onClick={() => void listen()}>Listen</button>
      <button type="button" className="secondary-button" disabled={!status?.speech_to_text || busy} onClick={() => void (recording ? stop() : start())}>{recording ? "Stop and transcribe" : "Record up to 15 seconds"}</button>
    </div>
    {status?.speech_to_text && <label className="speech-upload">Or upload a mono 16-bit PCM WAV file (30 seconds max)
      <input type="file" accept=".wav,audio/wav" disabled={busy || recording} onChange={(event) => { const file = event.target.files?.[0]; if (file) void transcribe(file); event.target.value = ""; }} />
    </label>}
    {busy && <p role="status">Transcribing locally...</p>}
    {result && <div className="speech-result"><strong>What the recognizer heard</strong><p>{result.text || "No words recognized. Try speaking closer to the microphone."}</p><small>{result.note} Compare it with the phrase yourself; no pronunciation score is calculated.</small></div>}
    {error && <p className="panel-error" role="alert">{error}</p>}
  </section>;
}
