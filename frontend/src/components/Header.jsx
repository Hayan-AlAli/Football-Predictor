/**
 * Header Component
 * App header with logo and stats
 */
export default function Header({ matchCount = 0 }) {
    return (
        <header className="header">
            <div className="container header-content">
                <div className="logo">
                    <span className="logo-icon">⚽</span>
                    <span className="logo-text">Football Predictor</span>
                </div>

                <div className="header-stats">
                    <div className="stat-item">
                        <div className="stat-value">{matchCount}</div>
                        <div className="stat-label">Matches</div>
                    </div>
                    <div className="stat-item">
                        <div className="stat-value">AI</div>
                        <div className="stat-label">Powered</div>
                    </div>
                </div>
            </div>
        </header>
    );
}
