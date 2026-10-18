import { useState } from "react";
import { login, register } from "../services/studentApi";
import { registerTeacher } from "../services/teacherApi";
import type { StudentSession } from "../types/student";

export default function StudentAccount({ onSignedIn, kind = "student" }: { onSignedIn: (session: StudentSession) => void; kind?: "student" | "teacher" }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [teacherCode, setTeacherCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { onSignedIn(mode === "register" ? kind === "teacher" ? await registerTeacher(email, password, name, teacherCode) : await register(email, password, name) : await login(email, password)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to sign in."); }
    finally { setBusy(false); }
  }

  return <section className="student-panel student-account" aria-label={`${kind} account`}>
    <h2>{mode === "register" ? `Create ${kind} account` : `${kind === "teacher" ? "Teacher" : "Student"} sign in`}</h2>
    <p>{kind === "teacher" ? "Manage your courses, assignments, and student progress. Teacher registration needs the code configured on this server." : "Sign in to save quiz attempts and track your study progress on this computer."}</p>
    <form onSubmit={(event) => void submit(event)}>
      {mode === "register" && <label>Display name<input value={name} maxLength={80} required onChange={(event) => setName(event.target.value)} /></label>}
      <label>Email<input type="email" value={email} autoComplete="email" required onChange={(event) => setEmail(event.target.value)} /></label>
      <label>Password<input type="password" value={password} minLength={mode === "register" ? 8 : undefined} autoComplete={mode === "register" ? "new-password" : "current-password"} required onChange={(event) => setPassword(event.target.value)} /></label>
      {mode === "register" && kind === "teacher" && <label>Teacher registration code<input type="password" value={teacherCode} required onChange={(event) => setTeacherCode(event.target.value)} /></label>}
      <button className="learning-primary" disabled={busy}>{busy ? "Please wait..." : mode === "register" ? "Create account" : "Sign in"}</button>
    </form>
    <button type="button" className="secondary-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "I have an account"}</button>
    {error && <p className="panel-error" role="alert">{error}</p>}
  </section>;
}
