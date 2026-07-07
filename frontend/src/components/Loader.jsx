/**
 * Loader Component
 * Displays loading spinner with optional message
 */
export default function Loader({ message = 'Loading...' }) {
    return (
        <div className="loading-container">
            <div className="spinner"></div>
            <span className="loading-text">{message}</span>
        </div>
    );
}
