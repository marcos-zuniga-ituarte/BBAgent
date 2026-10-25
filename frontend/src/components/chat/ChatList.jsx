import SidebarActionButton from './SidebarActionButton.jsx'

function ChatList({
                      chats,
                      loading,
                      selectedChatId,
                      onSelectChat,
                  }) {
    if (loading) {
        return <p style={styles.info}>Cargando chats...</p>
    }

    if (chats.length === 0) {
        return <p style={styles.info}>No hay chats todavía</p>
    }

    return (
        <div style={styles.list}>
            {chats.map((chat) => (
                <SidebarActionButton
                    key={chat.id}
                    onClick={() => onSelectChat(chat.id)}
                    active={selectedChatId === chat.id}
                    fullWidth
                    text={chat.title || `Chat ${chat.id.slice(0, 8)}`}
                    title={chat.title || `Chat ${chat.id.slice(0, 8)}`}
                    ariaLabel={chat.title || `Chat ${chat.id.slice(0, 8)}`}
                />
            ))}
        </div>
    )
}

const styles = {
    list: {
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
    },
    info: {
        color: '#6b7280',
        fontSize: '14px',
    },
    icon: {
        width: '18px',
        height: '18px',
        flexShrink: 0,
        display: 'block',
    },
}

export default ChatList