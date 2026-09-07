import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileAudio,
  KeyRound,
  Lock,
  Settings2,
  UploadCloud,
  Unlock,
} from 'lucide-react';

const embedSteps = [
  {
    number: '01',
    title: 'Choose a carrier',
    text: 'On Embed Payload, select or drop a non-empty 16-bit PCM WAV file. This is the audio container that will carry the payload.',
    icon: UploadCloud,
  },
  {
    number: '02',
    title: 'Enter the payload and key',
    text: 'Type the message into Secure Payload and enter a key. Keep the exact key: it is required to recover the message later.',
    icon: KeyRound,
  },
  {
    number: '03',
    title: 'Choose the settings',
    text: 'Encryption is enabled by default. Select Low, Medium, or High adaptivity, and optionally choose a custom output filename.',
    icon: Settings2,
  },
  {
    number: '04',
    title: 'Initialize embedding',
    text: 'Select Initialize Embedding. The generated stego WAV downloads automatically and is added to the current session for extraction and analysis.',
    icon: CheckCircle2,
  },
];

const extractSteps = [
  {
    number: '01',
    title: 'Choose the source',
    text: 'Use Session Files for a file created in this session, or choose Manual Upload to select a stego WAV from your device.',
    icon: FileAudio,
  },
  {
    number: '02',
    title: 'Provide the same key',
    text: 'Enter the key used during embedding. A different key will not recover the original payload.',
    icon: KeyRound,
  },
  {
    number: '03',
    title: 'Match manual settings',
    text: 'For an uploaded file, set Payload is AES Encrypted and Adaptivity Envelope to the values used during embedding. Session files apply these values automatically.',
    icon: Settings2,
  },
  {
    number: '04',
    title: 'Initialize extraction',
    text: 'Select Initialize Extraction. A verified text payload appears in Decoded Intelligence when recovery succeeds.',
    icon: Unlock,
  },
];

function StepList({ steps }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {steps.map(({ number, title, text, icon: Icon }) => (
        <article key={number} className="rounded-xl border border-theme-border bg-theme-base/35 p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-[10px] tracking-[0.2em] text-theme-accent">STEP {number}</span>
            <Icon size={17} className="text-theme-accent" strokeWidth={1.7} />
          </div>
          <h3 className="mb-1 text-sm font-semibold text-theme-text-main">{title}</h3>
          <p className="text-sm leading-relaxed text-theme-text-muted">{text}</p>
        </article>
      ))}
    </div>
  );
}

function GuideCard({ icon: Icon, eyebrow, title, children, className = '' }) {
  return (
    <section className={`glass-panel rounded-2xl p-6 md:p-7 ${className}`}>
      <div className="mb-5 flex items-start gap-3">
        <div className="rounded-xl border border-theme-border bg-theme-base/50 p-2.5 text-theme-accent">
          <Icon size={19} strokeWidth={1.6} />
        </div>
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-theme-accent">{eyebrow}</p>
          <h2 className="text-xl font-semibold text-theme-text-main">{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

export default function UserGuidePage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header className="max-w-3xl">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-theme-border bg-theme-border/20 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-theme-accent">
          <BookOpen size={12} /> User Guide
        </div>
        <h1 className="mb-3 text-4xl font-bold tracking-tight text-theme-text-main">How to use StegoResearch</h1>
        <p className="leading-relaxed text-theme-text-muted">
          StegoResearch places a text payload inside a WAV audio carrier, then reconstructs it from the generated stego file using the matching key and embedding settings. The Secure Vault keeps session artifacts available, while Visualizations compares carrier and stego signal data.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <GuideCard icon={UploadCloud} eyebrow="Before you begin" title="Prepare these items">
          <ul className="space-y-3 text-sm leading-relaxed text-theme-text-muted">
            <li className="flex gap-3"><FileAudio size={16} className="mt-0.5 shrink-0 text-theme-accent" />A non-empty 16-bit PCM WAV file to use as the carrier.</li>
            <li className="flex gap-3"><KeyRound size={16} className="mt-0.5 shrink-0 text-theme-accent" />A message and a key. Keep the key available for extraction.</li>
            <li className="flex gap-3"><Lock size={16} className="mt-0.5 shrink-0 text-theme-accent" />Complete vault setup or log in when using protected areas such as extraction, the vault, and visualizations.</li>
          </ul>
        </GuideCard>

        <GuideCard icon={ArrowRight} eyebrow="The workflow" title="Carrier in, payload out">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-center text-xs">
            <div className="rounded-xl border border-theme-border bg-theme-base/35 px-3 py-4 text-theme-text-main">Cover WAV</div>
            <ArrowRight size={16} className="text-theme-accent" />
            <div className="rounded-xl border border-theme-accent/40 bg-theme-accent/10 px-3 py-4 text-theme-text-main">Stego WAV</div>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-theme-text-muted">The original cover remains separate. The downloaded output is the stego WAV used for later recovery.</p>
        </GuideCard>
      </div>

      <GuideCard icon={UploadCloud} eyebrow="Embedding" title="Hide a message in audio">
        <StepList steps={embedSteps} />
      </GuideCard>

      <GuideCard icon={Unlock} eyebrow="Extraction" title="Recover a hidden message">
        <StepList steps={extractSteps} />
      </GuideCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <GuideCard icon={FileAudio} eyebrow="Files and formats" title="What the files mean">
          <dl className="space-y-4 text-sm">
            <div><dt className="font-semibold text-theme-text-main">Cover WAV</dt><dd className="mt-1 leading-relaxed text-theme-text-muted">The original audio carrier selected before embedding.</dd></div>
            <div><dt className="font-semibold text-theme-text-main">Stego WAV</dt><dd className="mt-1 leading-relaxed text-theme-text-muted">The generated WAV containing the embedded payload. It is downloaded after a successful embedding.</dd></div>
            <div><dt className="font-semibold text-theme-text-main">Payload</dt><dd className="mt-1 leading-relaxed text-theme-text-muted">The text entered in the Secure Payload field. The application records its size and embedding metrics in the session vault.</dd></div>
          </dl>
          <div className="mt-5 rounded-xl border border-theme-border bg-theme-base/35 p-4 text-sm leading-relaxed text-theme-text-muted">
            The upload controls accept <strong className="text-theme-text-main">.wav</strong> files only. The interface specifies 16-bit PCM WAV. Other audio extensions and invalid or empty WAV files are rejected.
          </div>
        </GuideCard>

        <GuideCard icon={Settings2} eyebrow="Settings" title="Adaptivity and encryption">
          <div className="space-y-4 text-sm leading-relaxed text-theme-text-muted">
            <p><strong className="text-theme-text-main">Encryption:</strong> enabled by default during embedding. Extraction must use the same encryption setting.</p>
            <p><strong className="text-theme-text-main">Adaptivity:</strong> Low uses the 0 percentile threshold, Medium uses 20, and High uses 40. Higher levels trade available capacity for more selective placement.</p>
            <p>For a generated session file, the application keeps the embed settings and applies them during extraction. For a manually uploaded file, you must match them yourself.</p>
          </div>
        </GuideCard>
      </div>

      <GuideCard icon={AlertTriangle} eyebrow="Troubleshooting" title="When recovery does not work">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-theme-border bg-theme-base/35 p-4"><h3 className="mb-1 text-sm font-semibold text-theme-text-main">Invalid key</h3><p className="text-sm leading-relaxed text-theme-text-muted">Re-enter the exact key used during embedding. Keys are case-sensitive in practice because the entered text is used to derive the extraction key.</p></div>
          <div className="rounded-xl border border-theme-border bg-theme-base/35 p-4"><h3 className="mb-1 text-sm font-semibold text-theme-text-main">Corrupted payload</h3><p className="text-sm leading-relaxed text-theme-text-muted">Confirm that the selected file is the generated stego WAV and that encryption and adaptivity match the original settings.</p></div>
          <div className="rounded-xl border border-theme-border bg-theme-base/35 p-4"><h3 className="mb-1 text-sm font-semibold text-theme-text-main">File rejected</h3><p className="text-sm leading-relaxed text-theme-text-muted">Use a readable, non-empty 16-bit PCM WAV file. Rename the file only if needed; changing its extension does not convert its audio format.</p></div>
          <div className="rounded-xl border border-theme-border bg-theme-base/35 p-4"><h3 className="mb-1 text-sm font-semibold text-theme-text-main">No session file listed</h3><p className="text-sm leading-relaxed text-theme-text-muted">Use Manual Upload with the downloaded stego WAV, or refresh the page and check the Secure Vault for generated session artifacts.</p></div>
        </div>
      </GuideCard>

      <p className="pb-4 text-center text-xs text-theme-text-muted">For reliable recovery, preserve the generated stego WAV and the exact key and embed settings used to create it.</p>
    </div>
  );
}
