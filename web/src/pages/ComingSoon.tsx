export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl2 border border-dashed border-ink-900/10 bg-white py-24 text-center">
      <img src="/icons/Illustrations/ai-workflow.svg" alt="" className="mb-6 h-32 w-32" />
      <h1 className="text-xl font-semibold text-ink-900">{title}</h1>
      <p className="mt-2 max-w-sm text-sm text-ink-500">
        This part of the AI Engineering Workspace lands in a later phase (see the roadmap in
        docs/VOYAGER_MASTER_BLUEPRINT.md). Phase 2 focused on the Travel Workspace backend and UI.
      </p>
    </div>
  );
}
