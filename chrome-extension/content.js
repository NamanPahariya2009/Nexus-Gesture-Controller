const overlay = document.createElement('div');
overlay.id = 'nexus-gesture-overlay';
overlay.style.position = 'fixed';
overlay.style.bottom = '20px';
overlay.style.right = '20px';
overlay.style.padding = '12px 20px';
overlay.style.background = 'rgba(20, 20, 20, 0.7)';
overlay.style.backdropFilter = 'blur(10px)';
overlay.style.borderRadius = '12px';
overlay.style.color = '#fff';
overlay.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
overlay.style.fontSize = '13px';
overlay.style.zIndex = '999999';
overlay.style.display = 'flex';
overlay.style.alignItems = 'center';
overlay.style.gap = '10px';
overlay.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.2)';
overlay.style.border = '1px solid rgba(255, 255, 255, 0.12)';
overlay.style.transition = 'all 0.25s ease';
overlay.style.opacity = '0';
overlay.style.pointerEvents = 'none';

const dot = document.createElement('div');
dot.style.width = '8px';
dot.style.height = '8px';
dot.style.borderRadius = '50%';
dot.style.background = '#ff4444';
dot.style.transition = 'background 0.3s ease';

const text = document.createElement('span');
text.innerText = 'Disconnected';
text.style.fontWeight = '500';

overlay.appendChild(dot);
overlay.appendChild(text);
document.body.appendChild(overlay);

const gestureLabels = {
    'MOVE': 'MOVE',
    'CLICK_LEFT': 'CLICK',
    'CLICK_RIGHT': 'RIGHT CLICK',
    'DOUBLE_CLICK': 'DOUBLE CLICK',
    'SCROLL': 'SCROLL',
    'VOLUME': 'VOLUME',
    'SWIPE': 'SWIPE',
    'FIST': 'FIST',
    'DRAG_ACTIVE': 'DRAGGING',
    'ZOOM': 'ZOOM',
    'IDLE': 'IDLE',
    'SLEEPING': 'PAUSED',
    'SLEEP_TOGGLE': 'WAIT',
};

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'GESTURE_UPDATE') {
        const data = request.data;
        overlay.style.opacity = '1';

        if (data.mode === 'SLEEPING') {
            dot.style.background = '#ff4444';
            dot.style.boxShadow = 'none';
            overlay.style.border = '1px solid #ff4444';
            text.innerText = 'PAUSED (Hold Middle Finger to Resume)';
            overlay.style.opacity = '0.7';
        } else if (data.mode === 'SLEEP_TOGGLE') {
            dot.style.background = '#ffbb33';
            text.innerText = 'Switching state...';
        } else {
            if (data.hand_detected) {
                dot.style.background = '#00C851';
                dot.style.boxShadow = '0 0 8px #00C851';
                overlay.style.border = '1px solid rgba(255, 255, 255, 0.12)';
            } else {
                dot.style.background = '#ffbb33';
                dot.style.boxShadow = 'none';
            }
            const label = gestureLabels[data.gesture] || data.mode;
            text.innerText = `${label} | ${data.fps} FPS`;
        }

        if (data.gesture === 'CLICK_LEFT' || data.gesture === 'DOUBLE_CLICK') {
            overlay.style.transform = 'scale(1.05)';
            setTimeout(() => overlay.style.transform = 'scale(1)', 100);
        }
    }
});
