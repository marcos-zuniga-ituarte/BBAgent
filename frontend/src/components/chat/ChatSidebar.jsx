import { useState } from 'react'
import BrandIcon from '../BrandIcon.jsx'
import ChatList from './ChatList'
import ConfigurationModal from './ConfigurationModal'
import {
    getSidebarCollapsedPreference,
    setSidebarCollapsedPreference,
} from '../../utils/sidebarPreference'
import SidebarActionButton from './SidebarActionButton.jsx'

function SettingsIcon({ size = 22, strokeWidth = 1.8 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
                d="M9.5 3h5l.6 2.6 2.2 1.3 2.5-.8 2.5 4.3-1.9 1.8v2.6l1.9 1.8-2.5 4.3-2.5-.8-2.2 1.3-.6 2.6h-5l-.6-2.6-2.2-1.3-2.5.8-2.5-4.3 1.9-1.8v-2.6l-1.9-1.8 2.5-4.3 2.5.8 2.2-1.3L9.5 3Z"
                transform="translate(1 0) scale(.9)"
                stroke="currentColor" strokeWidth={strokeWidth} strokeLinejoin="round"
            />
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth={strokeWidth}/>
        </svg>
    )
}

function PlusIcon({ size = 24 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
    )
}

function ChevronLeftIcon({ size = 18, strokeWidth = 2 }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
        >
            <path
                d="M15 6L9 12L15 18"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    )
}

function CloseIcon({ size = 18, strokeWidth = 2 }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
        >
            <path
                d="M6 6L18 18"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
            />
            <path
                d="M18 6L6 18"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
            />
        </svg>
    )
}

function ChatSidebar({
                         chats,
                         loading,
                         selectedChatId,
                         creatingChat,
                         onSelectChat,
                         onNewChat,
                         onLogout,
                         onConfigClose,
                         isMobile,
                         isMobileOpen,
                         onCloseMobile,
                     }) {
    const [isConfigOpen, setIsConfigOpen] = useState(false)
    const [isCollapsed, setIsCollapsed] = useState(() =>
        getSidebarCollapsedPreference()
    )

    function handleCloseConfig() {
        setIsConfigOpen(false)
        onConfigClose?.()
    }

    function toggleCollapsed() {
        setIsCollapsed((prev) => {
            const next = !prev
            setSidebarCollapsedPreference(next)
            return next
        })
    }

    function handleNewChatClick() {
        onNewChat?.()

        if (isMobile) {
            onCloseMobile?.()
        }
    }

    function handleSelectChatClick(id) {
        onSelectChat?.(id)

        if (isMobile) {
            onCloseMobile?.()
        }
    }

    const sidebarStyle = {
        ...styles.sidebar,
        ...(isMobile
            ? isMobileOpen
                ? styles.sidebarMobileOpen
                : styles.sidebarMobileClosed
            : isCollapsed
                ? styles.sidebarCollapsed
                : {}),
    }

    const showExpandedContent = isMobile || !isCollapsed

    return (
        <>
            {isMobile && isMobileOpen ? (
                <div style={styles.mobileBackdrop} onClick={onCloseMobile} />
            ) : null}

            <aside className={`chat-sidebar${showExpandedContent ? '' : ' is-collapsed'}`} style={sidebarStyle}>
                <div style={styles.header}>
                    <div style={styles.topButtons}>
                        {isMobile ? (
                            <SidebarActionButton
                                onClick={onCloseMobile}
                                title="Cerrar menú"
                                ariaLabel="Cerrar menú"
                                icon={<CloseIcon size={18} />}
                            />
                        ) : (
                            <SidebarActionButton
                                onClick={toggleCollapsed}
                                ariaExpanded={!isCollapsed}
                                ariaControls="chat-sidebar-content"
                                title={
                                    isCollapsed
                                        ? 'Expandir sidebar'
                                        : 'Ocultar sidebar'
                                }
                                ariaLabel={
                                    isCollapsed
                                        ? 'Expandir sidebar'
                                        : 'Ocultar sidebar'
                                }
                                icon={
                                    <span className="sidebar-toggle-chevron" style={{ transform: isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                                        <ChevronLeftIcon size={18} />
                                    </span>
                                }
                            />
                        )}
                        <div className="sidebar-expanded-content" aria-hidden={!showExpandedContent} style={styles.brand}>
                            <BrandIcon size={32} />
                            <span style={styles.brandName}>BBAgent</span>
                        </div>
                    </div>

                    <SidebarActionButton
                        onClick={handleNewChatClick}
                        disabled={creatingChat}
                        icon={<PlusIcon />}
                        text="Nuevo chat"
                        collapsed={!showExpandedContent}
                        title="Nuevo chat"
                        ariaLabel="Nuevo chat"
                        fullWidth
                        stableIcon
                        primary
                    />

                    <div style={styles.divider} />
                </div>

                <div
                    id="chat-sidebar-content"
                    className="sidebar-scroll"
                    style={{ ...styles.listArea, overflowY: showExpandedContent ? 'auto' : 'hidden' }}
                    aria-hidden={!showExpandedContent}
                    inert={!showExpandedContent}
                >
                    <div className="sidebar-expanded-content sidebar-chat-list">
                        <ChatList
                            chats={chats}
                            loading={loading}
                            selectedChatId={selectedChatId}
                            onSelectChat={handleSelectChatClick}
                        />
                    </div>
                </div>

                <div style={styles.footer}>
                    <SidebarActionButton
                        onClick={() => setIsConfigOpen(true)}
                        title="Configuración"
                        ariaLabel="Configuración"
                        icon={<SettingsIcon size={22} />}
                        text="Configuración"
                        collapsed={!showExpandedContent}
                        fullWidth
                        stableIcon
                    />
                </div>
            </aside>

            <ConfigurationModal
                open={isConfigOpen}
                onClose={handleCloseConfig}
                onLogout={onLogout}
            />
        </>
    )
}

const styles = {
    sidebar: {
        width: '260px',
        height: '100vh',
        background: 'var(--sidebar-bg)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        overflow: 'hidden',
    },
    sidebarCollapsed: {
        width: '72px',
    },
    sidebarMobileOpen: {
        position: 'fixed',
        top: 0,
        left: 0,
        width: 'min(320px, 85vw)',
        height: '100vh',
        zIndex: 50,
        transform: 'translateX(0)',
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.28)',
    },
    sidebarMobileClosed: {
        position: 'fixed',
        top: 0,
        left: 0,
        width: 'min(320px, 85vw)',
        height: '100vh',
        zIndex: 50,
        transform: 'translateX(-100%)',
        boxShadow: 'none',
    },
    mobileBackdrop: {
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.35)',
        zIndex: 40,
    },
    header: {
        padding: '16px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
    },
    topButtons: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-start',
        height: '44px',
        gap: '12px',
    },
    divider: {
        height: '1px',
        background: 'var(--border)',
    },
    listArea: {
        flex: 1,
        minHeight: 0,
        overflowX: 'hidden',
        overflowY: 'auto',
        padding: '0 14px 14px',
    },
    footer: {
        padding: '12px 14px',
        borderTop: '1px solid var(--border)',
    },
    brand: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        flexShrink: 0,
        whiteSpace: 'nowrap',
    },
    brandName: {
        fontSize: '17px',
        fontWeight: 650,
        letterSpacing: '-0.3px',
        color: 'var(--text)',
    },
}

export default ChatSidebar
