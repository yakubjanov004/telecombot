export default function Layout({ children, fullWidth = false, home = false }) {
  return (
    <div className={`app-shell ${home ? 'app-shell--home' : ''}`}>
      <div className="app-shell__gradient" aria-hidden="true" />
      <div className="app-shell__grid" aria-hidden="true" />
      <main className={`app-main ${fullWidth ? 'app-main--full' : ''}`}>
        {children}
      </main>
    </div>
  );
}
