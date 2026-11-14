import { evidenceItems } from "@/lib/evidence";

export default function EvidencePage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-[0.18em] text-[#d7b56d]">SOURCE RECORD</p>
        <h1 className="mt-2 text-3xl font-semibold">Satellite evidence</h1>
        <p className="mt-2 max-w-3xl text-sm text-[#c9d5cf]">Values below are taken from the committed manifests and science notes. They are not new measurements.</p>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-white/10">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#93a39b]">
            <tr>
              <th className="px-4 py-3">Record</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Provenance</th>
            </tr>
          </thead>
          <tbody>
            {evidenceItems.map((item) => (
              <tr key={item.id} className="border-t border-white/10">
                <td className="px-4 py-3 font-medium">{item.title}</td>
                <td className="px-4 py-3 text-[#d7b56d]">{item.status}</td>
                <td className="px-4 py-3 font-mono text-xs text-[#c9d5cf]">{item.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {evidenceItems.map((item) => (
        <article key={item.id} className="rounded-2xl border border-white/10 p-5">
          <h2 className="text-xl font-medium">{item.title}</h2>
          <p className="mt-2 text-sm text-[#d7e2dc]">{item.summary}</p>
          <ul className="mt-4 space-y-2 text-sm text-[#c9d5cf]">
            {item.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}
