export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#E8EBF8] p-6 md:p-12">
      <div className="bg-white rounded-3xl shadow-sm w-full max-w-2xl mx-auto px-8 py-10 flex flex-col gap-6">

        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Privacy Policy</h1>
          <p className="mt-1 text-sm text-gray-400">Effective date: April 30, 2026</p>
        </div>

        <p className="text-gray-700">
          Claire ("we", "our", "the app") is a file organisation tool for students. This policy explains
          what data we handle, where it goes, and what we never do with it.
        </p>

        <Section title="What we read">
          <p>When you connect a Google Drive account, Claire reads:</p>
          <ul className="list-disc pl-5 mt-2 flex flex-col gap-1">
            <li>File names, sizes, types, and last-modified dates</li>
            <li>File content — only to classify files by school subject, processed entirely on your device (never sent to an external AI server)</li>
            <li>No file content is ever written to any server or third-party service</li>
          </ul>
        </Section>

        <Section title="What we store">
          <p>We store only a lightweight index containing:</p>
          <ul className="list-disc pl-5 mt-2 flex flex-col gap-1">
            <li>File names, sizes, types, and subject categories</li>
            <li>No file content. Ever.</li>
          </ul>
          <p className="mt-2">
            This index is saved to your own Google Drive's private appdata folder — a hidden
            area only your account and this app can access. It is never stored on any server.
          </p>
        </Section>

        <Section title="What we never do">
          <ul className="list-disc pl-5 flex flex-col gap-1">
            <li>We never send file content to any external server or AI service</li>
            <li>We never sell or share your data with third parties</li>
            <li>We never use your files to train AI models</li>
            <li>We never access files outside the Google Drive account you explicitly connect</li>
          </ul>
        </Section>

        <Section title="Google OAuth scopes we request">
          <ul className="list-disc pl-5 flex flex-col gap-1">
            <li><strong>drive.readonly</strong> — to read your file list and content for classification</li>
            <li><strong>drive.appdata</strong> — to save your file index in your own Drive's private appdata folder</li>
          </ul>
          <p className="mt-2">We request no other Google scopes.</p>
        </Section>

        <Section title="AI classification">
          <p>
            Claire uses Gemma (running locally via Ollama) to classify your files by school subject.
            All AI processing happens on your device. Your file content is never sent to any external
            AI service or API.
          </p>
        </Section>

        <Section title="Deleting your data">
          <p>
            You can delete all Claire data at any time:
          </p>
          <ul className="list-disc pl-5 mt-2 flex flex-col gap-1">
            <li>Disconnect your Drive account in Settings — this deletes the index from your Drive appdata</li>
            <li>Revoking Claire's Google permissions at <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">myaccount.google.com/permissions</a> removes all access</li>
            <li>Delete the <code className="text-sm bg-gray-100 px-1 rounded">~/.declutter/</code> folder to remove all local data</li>
          </ul>
        </Section>

        <Section title="Children's privacy">
          <p>
            Claire is designed for use by students in conjunction with their school. We do not knowingly
            collect personal information from children under 13 without verifiable parental or school consent.
            Schools using Claire for students are responsible for ensuring appropriate consent is in place.
          </p>
        </Section>

        <Section title="Contact">
          <p>
            Questions about this policy? Email us at{' '}
            <a href="mailto:rhduriseti@gmail.com" className="text-blue-600 hover:underline">
              rhduriseti@gmail.com
            </a>
          </p>
        </Section>

      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      <div className="text-gray-700 text-sm leading-relaxed">{children}</div>
    </div>
  )
}
