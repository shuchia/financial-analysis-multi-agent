// Chart.js for Dashboard Preview Animation

class DashboardChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.offsetWidth;
        this.height = this.canvas.offsetHeight;
        
        // Set canvas size
        this.canvas.width = this.width * window.devicePixelRatio;
        this.canvas.height = this.height * window.devicePixelRatio;
        this.canvas.style.width = this.width + 'px';
        this.canvas.style.height = this.height + 'px';
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        
        this.animationFrame = null;
        this.startTime = Date.now();
        
        // Chart data
        this.dataPoints = this.generateMockData();
        this.currentDataIndex = 0;
        this.animatedDataPoints = [];
        
        this.init();
    }
    
    generateMockData() {
        const points = [];
        const basePrice = 150;
        let currentPrice = basePrice;
        
        for (let i = 0; i < 50; i++) {
            // Generate realistic stock price movement
            const change = (Math.random() - 0.48) * 3; // Slight upward bias
            currentPrice += change;
            currentPrice = Math.max(currentPrice, basePrice * 0.8); // Don't go too low
            currentPrice = Math.min(currentPrice, basePrice * 1.4); // Don't go too high
            
            points.push({
                x: i,
                y: currentPrice,
                timestamp: Date.now() + i * 24 * 60 * 60 * 1000 // Daily data
            });
        }
        
        return points;
    }
    
    init() {
        this.animate();
    }
    
    animate() {
        this.clear();
        this.updateData();
        this.drawGrid();
        this.drawChart();
        this.drawCurrentPrice();
        
        this.animationFrame = requestAnimationFrame(() => this.animate());
    }
    
    clear() {
        this.ctx.clearRect(0, 0, this.width, this.height);
    }
    
    updateData() {
        const elapsed = Date.now() - this.startTime;
        const interval = 100; // Add new point every 100ms
        
        if (elapsed > this.currentDataIndex * interval && this.currentDataIndex < this.dataPoints.length) {
            this.animatedDataPoints.push(this.dataPoints[this.currentDataIndex]);
            this.currentDataIndex++;
        }
        
        // Reset animation when complete
        if (this.currentDataIndex >= this.dataPoints.length) {
            setTimeout(() => {
                this.startTime = Date.now();
                this.currentDataIndex = 0;
                this.animatedDataPoints = [];
            }, 2000);
        }
    }
    
    drawGrid() {
        const gridColor = '#f0f2f6';
        const gridSpacing = 20;
        
        this.ctx.strokeStyle = gridColor;
        this.ctx.lineWidth = 1;
        
        // Vertical lines
        for (let x = 0; x <= this.width; x += gridSpacing) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
        
        // Horizontal lines
        for (let y = 0; y <= this.height; y += gridSpacing) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }
    }
    
    drawChart() {
        if (this.animatedDataPoints.length < 2) return;
        
        const padding = 20;
        const chartWidth = this.width - padding * 2;
        const chartHeight = this.height - padding * 2;
        
        // Calculate price range
        const prices = this.animatedDataPoints.map(p => p.y);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const priceRange = maxPrice - minPrice;
        
        // Create gradient
        const gradient = this.ctx.createLinearGradient(0, 0, 0, this.height);
        gradient.addColorStop(0, 'rgba(255, 107, 53, 0.8)');
        gradient.addColorStop(1, 'rgba(26, 117, 159, 0.8)');
        
        // Draw area under curve
        this.ctx.fillStyle = 'rgba(255, 107, 53, 0.1)';
        this.ctx.beginPath();
        
        this.animatedDataPoints.forEach((point, index) => {
            const x = padding + (index / (this.dataPoints.length - 1)) * chartWidth;
            const y = padding + (1 - (point.y - minPrice) / priceRange) * chartHeight;
            
            if (index === 0) {
                this.ctx.moveTo(x, this.height - padding);
                this.ctx.lineTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        
        // Close the area
        if (this.animatedDataPoints.length > 0) {
            const lastX = padding + ((this.animatedDataPoints.length - 1) / (this.dataPoints.length - 1)) * chartWidth;
            this.ctx.lineTo(lastX, this.height - padding);
        }
        this.ctx.closePath();
        this.ctx.fill();
        
        // Draw line
        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = 3;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.beginPath();
        
        this.animatedDataPoints.forEach((point, index) => {
            const x = padding + (index / (this.dataPoints.length - 1)) * chartWidth;
            const y = padding + (1 - (point.y - minPrice) / priceRange) * chartHeight;
            
            if (index === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        
        this.ctx.stroke();
        
        // Draw data points
        this.ctx.fillStyle = '#FF6B35';
        this.animatedDataPoints.forEach((point, index) => {
            const x = padding + (index / (this.dataPoints.length - 1)) * chartWidth;
            const y = padding + (1 - (point.y - minPrice) / priceRange) * chartHeight;
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, 3, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }
    
    drawCurrentPrice() {
        if (this.animatedDataPoints.length === 0) return;
        
        const currentPoint = this.animatedDataPoints[this.animatedDataPoints.length - 1];
        const price = currentPoint.y.toFixed(2);
        
        // Draw price label
        this.ctx.fillStyle = '#FF6B35';
        this.ctx.font = 'bold 14px Inter, sans-serif';
        this.ctx.textAlign = 'right';
        this.ctx.fillText(`$${price}`, this.width - 10, 25);
        
        // Draw trend indicator
        if (this.animatedDataPoints.length > 1) {
            const prevPoint = this.animatedDataPoints[this.animatedDataPoints.length - 2];
            const change = currentPoint.y - prevPoint.y;
            const changePercent = ((change / prevPoint.y) * 100).toFixed(2);
            
            this.ctx.fillStyle = change >= 0 ? '#00BA6D' : '#E74C3C';
            this.ctx.font = '12px Inter, sans-serif';
            this.ctx.fillText(
                `${change >= 0 ? '+' : ''}${changePercent}%`,
                this.width - 10,
                45
            );
        }
    }
    
    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }
}

// Alternative simple chart for fallback
class SimpleChart {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.offsetWidth;
        this.height = this.canvas.offsetHeight;
        
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        
        this.draw();
    }
    
    draw() {
        const data = [120, 125, 118, 130, 135, 140, 138, 145, 150, 155];
        const padding = 20;
        const chartWidth = this.width - padding * 2;
        const chartHeight = this.height - padding * 2;
        
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min;
        
        // Create gradient
        const gradient = this.ctx.createLinearGradient(0, 0, 0, this.height);
        gradient.addColorStop(0, '#FF6B35');
        gradient.addColorStop(1, '#1A759F');
        
        // Draw line
        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        
        data.forEach((value, index) => {
            const x = padding + (index / (data.length - 1)) * chartWidth;
            const y = padding + (1 - (value - min) / range) * chartHeight;
            
            if (index === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        
        this.ctx.stroke();
        
        // Draw points
        this.ctx.fillStyle = '#FF6B35';
        data.forEach((value, index) => {
            const x = padding + (index / (data.length - 1)) * chartWidth;
            const y = padding + (1 - (value - min) / range) * chartHeight;
            
            this.ctx.beginPath();
            this.ctx.arc(x, y, 4, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }
}

// Initialize chart when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Try to create animated chart, fallback to simple chart
    try {
        new DashboardChart('preview-chart');
    } catch (error) {
        console.warn('Animated chart failed, using simple chart:', error);
        new SimpleChart('preview-chart');
    }
});

// Handle window resize
window.addEventListener('resize', () => {
    // Reinitialize chart on resize
    setTimeout(() => {
        const canvas = document.getElementById('preview-chart');
        if (canvas) {
            try {
                new DashboardChart('preview-chart');
            } catch (error) {
                new SimpleChart('preview-chart');
            }
        }
    }, 100);
});