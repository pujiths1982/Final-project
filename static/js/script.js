let detectionInterval;
let isDetecting = false;

function updateDetectionStats() {
    fetch('/detection_stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('totalDetections').textContent = data.total_detections;
            
            if (data.last_detection_time) {
                document.getElementById('lastDetection').textContent = data.last_detection_time;
            }
            
            const obstacleList = document.getElementById('obstacleList');
            
            if (data.current_obstacles && data.current_obstacles.length > 0) {
                obstacleList.innerHTML = '';
                
                const uniqueObstacles = {};
                data.current_obstacles.forEach(obstacle => {
                    if (!uniqueObstacles[obstacle.class] || 
                        uniqueObstacles[obstacle.class].confidence < obstacle.confidence) {
                        uniqueObstacles[obstacle.class] = obstacle;
                    }
                });
                
                Object.values(uniqueObstacles).forEach(obstacle => {
                    const obstacleItem = document.createElement('div');
                    obstacleItem.className = 'obstacle-item';
                    obstacleItem.innerHTML = `
                        <span class="obstacle-name">${obstacle.class}</span>
                        <span class="obstacle-confidence">${(obstacle.confidence * 100).toFixed(1)}%</span>
                    `;
                    obstacleList.appendChild(obstacleItem);
                });
                
                document.getElementById('alertOverlay').classList.add('active');
            } else {
                obstacleList.innerHTML = `
                    <div class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                            <circle cx="24" cy="24" r="20" stroke="#e0e0e0" stroke-width="2"/>
                            <path d="M24 16v16M16 24h16" stroke="#e0e0e0" stroke-width="2"/>
                        </svg>
                        <p>No obstacles detected</p>
                    </div>
                `;
                document.getElementById('alertOverlay').classList.remove('active');
            }
            
            const refreshIndicator = document.getElementById('refreshIndicator');
            refreshIndicator.classList.add('active');
            setTimeout(() => refreshIndicator.classList.remove('active'), 500);
        })
        .catch(error => {
            console.error('Error fetching detection stats:', error);
        });
}

function startDetection() {
    if (!isDetecting) {
        isDetecting = true;
        document.getElementById('systemStatus').textContent = 'Detecting...';
        document.querySelector('.status-dot').style.background = '#ff9800';
        
        document.getElementById('videoFeed').style.display = 'block';
        document.getElementById('videoFeed').src = '/video_feed?' + new Date().getTime();
        
        detectionInterval = setInterval(updateDetectionStats, 500);
        
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
    }
}

function stopDetection() {
    if (isDetecting) {
        isDetecting = false;
        document.getElementById('systemStatus').textContent = 'System Stopped';
        document.querySelector('.status-dot').style.background = '#f44336';
        
        clearInterval(detectionInterval);
        
        fetch('/stop_camera')
            .then(() => {
                document.getElementById('videoFeed').style.display = 'none';
                document.getElementById('alertOverlay').classList.remove('active');
                
                document.getElementById('totalDetections').textContent = '0';
                document.getElementById('lastDetection').textContent = 'No detections yet';
                document.getElementById('obstacleList').innerHTML = `
                    <div class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                            <circle cx="24" cy="24" r="20" stroke="#e0e0e0" stroke-width="2"/>
                            <path d="M24 16v16M16 24h16" stroke="#e0e0e0" stroke-width="2"/>
                        </svg>
                        <p>No obstacles detected</p>
                    </div>
                `;
            });
        
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
    }
}

document.getElementById('startBtn').addEventListener('click', startDetection);
document.getElementById('stopBtn').addEventListener('click', stopDetection);

document.getElementById('stopBtn').disabled = true;

window.addEventListener('beforeunload', function() {
    if (isDetecting) {
        fetch('/stop_camera');
    }
});