import { useAuth } from '../hooks/useAuth';

interface LabelStudioEmbedProps {
  path?: string;
}

export function LabelStudioEmbed({ path = '/projects' }: LabelStudioEmbedProps) {
  const { user, logout } = useAuth();

  // The iframe src points to our proxy endpoint
  // This makes Label Studio same-origin with our app
  const iframeSrc = `/ls${path}`;

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.title}>Label Studio</h1>
          <div style={styles.userSection}>
            <span style={styles.userEmail}>{user?.email}</span>
            <button onClick={logout} style={styles.logoutButton}>
              Logout
            </button>
          </div>
        </div>
      </header>

      <div style={styles.iframeContainer}>
        <iframe
          src={iframeSrc}
          style={styles.iframe}
          title="Label Studio"
          allow="clipboard-write"
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    width: '100vw',
  },
  header: {
    backgroundColor: '#1f2937',
    color: 'white',
    padding: '0.75rem 1rem',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  },
  headerContent: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    maxWidth: '1400px',
    margin: '0 auto',
    width: '100%',
  },
  title: {
    fontSize: '1.25rem',
    fontWeight: 'bold',
    margin: 0,
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  userEmail: {
    fontSize: '0.875rem',
    color: '#d1d5db',
  },
  logoutButton: {
    padding: '0.5rem 1rem',
    backgroundColor: 'transparent',
    color: 'white',
    border: '1px solid #4b5563',
    borderRadius: '4px',
    fontSize: '0.875rem',
    cursor: 'pointer',
  },
  iframeContainer: {
    flex: 1,
    overflow: 'hidden',
  },
  iframe: {
    width: '100%',
    height: '100%',
    border: 'none',
  },
};
