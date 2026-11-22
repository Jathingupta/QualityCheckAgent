function App() {
  const milestones = [
    ["Project foundation", "Configuration, API shell, frontend shell and initial checks"],
    ["Quality Playbook installation", "Pin the official upstream package and preserve notices"],
    ["Repository ingestion", "Safe repository intake and workspace isolation"],
    ["LLM provider abstraction", "Provider adapters, credentials and usage controls"],
    ["Workflow orchestration", "LangGraph state, phase boundaries and checkpoints"],
    ["Official quality phases", "Explore, Generate, Review, Audit, Reconcile and Verify"],
    ["Iteration strategies", "Additional defect discovery and evidence reconciliation"],
    ["Persistence and recovery", "Run history, artifacts and resumable execution"],
    ["API and dashboard", "Connect the interface to real audit workflows"],
    ["Final verification", "End-to-end, security and reproducibility checks"],
  ];

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">Q</div>
        <div><p className="eyebrow">QUALITY ENGINEERING WORKSPACE</p><h1>QualityCheckAgent</h1></div>
        <span className="status">Foundation stage</span>
      </header>
      <section className="welcome-card" aria-labelledby="welcome-title">
        <p className="eyebrow">REPOSITORY QUALITY PLATFORM</p>
        <h2 id="welcome-title">A more rigorous way to inspect codebases.</h2>
        <p className="intro">The project foundation is in place. Repository connection, the official Quality Playbook workflow, provider configuration, and audit history will be introduced in subsequent milestones.</p>
        <div className="progress-track" aria-label="Milestone 1 of 10"><span /></div>
        <p className="progress-label">Milestone 1 of 10 · Project foundation</p>
      </section>
      <section className="phase-section" aria-labelledby="roadmap-title">
        <div className="section-heading"><div><p className="eyebrow">DELIVERY PLAN</p><h2 id="roadmap-title">Development milestones</h2></div><span className="count">10 milestones</span></div>
        <ol className="milestone-list">
          {milestones.map(([title, description], index) => (
            <li className={index === 0 ? "complete" : ""} key={title}>
              <span className="step">{String(index + 1).padStart(2, "0")}</span>
              <div><strong>{title}</strong><small>{description}</small></div>
              {index === 0 && <span className="tag">In progress</span>}
            </li>
          ))}
        </ol>
      </section>
      <footer>Built incrementally · Each milestone must pass its checks before the next begins.</footer>
    </main>
  );
}

export default App;
