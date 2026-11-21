export function Warnings({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null
  return (
    <div className="alert alert-note" role="note">
      {warnings.map((w) => <p key={w}>{w}</p>)}
    </div>
  )
}
