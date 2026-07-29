'use strict';

var Spectrum = (function () {
    var currentLevel = 0;
    var currentRange = { min: 0, max: 0 };

    var LEVELS = [
        {
            level: 1,
            name: 'Level 1 - 低分辨率',
            badgeClass: 'level-low',
            minWidth: 0,
            minHeight: 0,
            spectralMin: 500,
            spectralMax: 650,
            description: '限制频段'
        },
        {
            level: 2,
            name: 'Level 2 - 中分辨率',
            badgeClass: 'level-mid',
            minWidth: 1280,
            minHeight: 720,
            spectralMin: 440,
            spectralMax: 720,
            description: '扩展频段'
        },
        {
            level: 3,
            name: 'Level 3 - 高分辨率',
            badgeClass: 'level-high',
            minWidth: 1920,
            minHeight: 1080,
            spectralMin: 400,
            spectralMax: 760,
            description: '广域频段'
        },
        {
            level: 4,
            name: 'Level 4 - 超高清',
            badgeClass: 'level-ultra',
            minWidth: 2560,
            minHeight: 1440,
            spectralMin: 380,
            spectralMax: 780,
            description: '全光谱范围'
        }
    ];

    function wavelengthToRGB(wavelength) {
        var r = 0, g = 0, b = 0;

        if (wavelength >= 380 && wavelength < 440) {
            r = -(wavelength - 440) / (440 - 380);
            g = 0;
            b = 1;
        } else if (wavelength >= 440 && wavelength < 490) {
            r = 0;
            g = (wavelength - 440) / (490 - 440);
            b = 1;
        } else if (wavelength >= 490 && wavelength < 510) {
            r = 0;
            g = 1;
            b = -(wavelength - 510) / (510 - 490);
        } else if (wavelength >= 510 && wavelength < 580) {
            r = (wavelength - 510) / (580 - 510);
            g = 1;
            b = 0;
        } else if (wavelength >= 580 && wavelength < 645) {
            r = 1;
            g = -(wavelength - 645) / (645 - 580);
            b = 0;
        } else if (wavelength >= 645 && wavelength <= 780) {
            r = 1;
            g = 0;
            b = 0;
        }

        var factor = 0;
        if (wavelength >= 380 && wavelength < 420) {
            factor = 0.3 + 0.7 * (wavelength - 380) / (420 - 380);
        } else if (wavelength >= 420 && wavelength <= 700) {
            factor = 1;
        } else if (wavelength > 700 && wavelength <= 780) {
            factor = 0.3 + 0.7 * (780 - wavelength) / (780 - 700);
        }

        r = Math.round(clamp(r * factor, 0, 1) * 255);
        g = Math.round(clamp(g * factor, 0, 1) * 255);
        b = Math.round(clamp(b * factor, 0, 1) * 255);

        return { r: r, g: g, b: b };
    }

    function clamp(value, min, max) {
        return value < min ? min : (value > max ? max : value);
    }

    function rgbToHex(r, g, b) {
        var toHex = function (n) {
            var s = n.toString(16);
            return s.length === 1 ? '0' + s : s;
        };
        return ('#' + toHex(r) + toHex(g) + toHex(b)).toUpperCase();
    }

    function getWavelengthRegion(wavelength) {
        if (wavelength >= 380 && wavelength < 450) return '紫色 (Violet)';
        if (wavelength >= 450 && wavelength < 495) return '蓝色 (Blue)';
        if (wavelength >= 495 && wavelength < 570) return '绿色 (Green)';
        if (wavelength >= 570 && wavelength < 590) return '黄色 (Yellow)';
        if (wavelength >= 590 && wavelength < 620) return '橙色 (Orange)';
        if (wavelength >= 620 && wavelength <= 780) return '红色 (Red)';
        return '可见光外';
    }

    function detectResolutionLevel() {
        var screenWidth = screen.width;
        var screenHeight = screen.height;
        var windowWidth = window.innerWidth;
        var windowHeight = window.innerHeight;

        var effectiveWidth = Math.max(screenWidth, windowWidth);
        var effectiveHeight = Math.max(screenHeight, windowHeight);

        var matchedLevel = LEVELS[0];
        for (var i = LEVELS.length - 1; i >= 0; i--) {
            var lvl = LEVELS[i];
            if (effectiveWidth >= lvl.minWidth && effectiveHeight >= lvl.minHeight) {
                matchedLevel = lvl;
                break;
            }
        }

        return {
            level: matchedLevel,
            screenWidth: screenWidth,
            screenHeight: screenHeight,
            windowWidth: windowWidth,
            windowHeight: windowHeight,
            effectiveWidth: effectiveWidth,
            effectiveHeight: effectiveHeight,
            dpr: window.devicePixelRatio || 1,
            colorDepth: screen.colorDepth || 24
        };
    }

    function setTextContent(id, text) {
        var el = document.getElementById(id);
        if (el) {
            el.textContent = text;
        }
    }

    function updateDeviceInfoDisplay(info) {
        setTextContent('screen-resolution', info.screenWidth + ' x ' + info.screenHeight + ' px');
        setTextContent('window-size', info.windowWidth + ' x ' + info.windowHeight + ' px');
        setTextContent('device-pixel-ratio', info.dpr + 'x' + (info.dpr > 1 ? ' (HiDPI/Retina)' : ' (Standard)'));
        setTextContent('color-depth', info.colorDepth + ' bits' + (info.colorDepth >= 24 ? ' (真彩色)' : ''));

        var levelBadge = document.createElement('span');
        levelBadge.className = 'level-badge ' + info.level.badgeClass;
        levelBadge.textContent = 'Level ' + info.level.level;

        var levelEl = document.getElementById('resolution-level');
        if (levelEl) {
            levelEl.textContent = '';
            levelEl.appendChild(levelBadge);
            var descSpan = document.createElement('span');
            descSpan.textContent = ' - ' + info.level.description;
            levelEl.appendChild(descSpan);
        }

        var rangeText = info.level.spectralMin + 'nm ~ ' + info.level.spectralMax + 'nm';
        if (info.level.level < 4) {
            var diffLow = info.level.spectralMin - 380;
            var diffHigh = 780 - info.level.spectralMax;
            rangeText += ' (屏蔽 ' + diffLow + 'nm 低频 + ' + diffHigh + 'nm 高频)';
        } else {
            rangeText += ' (完整可见光谱)';
        }
        setTextContent('spectral-range', rangeText);
        setTextContent('spectrum-range-label', '波长范围: ' + info.level.spectralMin + ' - ' + info.level.spectralMax + ' nm');

        currentLevel = info.level.level;
        currentRange.min = info.level.spectralMin;
        currentRange.max = info.level.spectralMax;
    }

    function drawSpectrumCanvas() {
        var canvas = document.getElementById('spectrum-canvas');
        if (!canvas) return;

        var container = canvas.parentElement;
        if (!container) return;

        var containerWidth = container.clientWidth;
        if (containerWidth <= 0) containerWidth = 800;
        var displayHeight = 120;
        var dpr = window.devicePixelRatio || 1;

        canvas.style.width = containerWidth + 'px';
        canvas.style.height = displayHeight + 'px';
        canvas.width = Math.floor(containerWidth * dpr);
        canvas.height = Math.floor(displayHeight * dpr);

        var ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.scale(dpr, dpr);

        var width = containerWidth;
        var height = displayHeight;

        var totalMin = 380;
        var totalMax = 780;
        var allowedMin = currentRange.min || 500;
        var allowedMax = currentRange.max || 650;

        ctx.clearRect(0, 0, width, height);

        var gradientAreaHeight = height - 30;
        var intensityAreaHeight = 20;
        var intensityTop = gradientAreaHeight + 5;

        for (var x = 0; x < width; x++) {
            var wavelength = totalMin + (totalMax - totalMin) * (x / width);
            var inRange = wavelength >= allowedMin && wavelength <= allowedMax;
            var rgb;

            if (inRange) {
                rgb = wavelengthToRGB(wavelength);
            } else {
                var dist = 0;
                if (wavelength < allowedMin) {
                    dist = (allowedMin - wavelength) / (allowedMin - totalMin);
                } else {
                    dist = (wavelength - allowedMax) / (totalMax - allowedMax);
                }
                dist = clamp(dist, 0, 1);
                var fullRgb = wavelengthToRGB(wavelength);
                var grayVal = Math.round(30 + dist * 20);
                rgb = {
                    r: Math.round(fullRgb.r * (1 - dist) * 0.3 + grayVal),
                    g: Math.round(fullRgb.g * (1 - dist) * 0.3 + grayVal),
                    b: Math.round(fullRgb.b * (1 - dist) * 0.3 + grayVal)
                };
            }

            ctx.fillStyle = 'rgb(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ')';
            ctx.fillRect(x, 0, 1, gradientAreaHeight);
        }

        for (var y = 0; y < intensityAreaHeight; y++) {
            for (var x2 = 0; x2 < width; x2++) {
                var wl2 = totalMin + (totalMax - totalMin) * (x2 / width);
                var inRange2 = wl2 >= allowedMin && wl2 <= allowedMax;

                if (inRange2) {
                    var rgb2 = wavelengthToRGB(wl2);
                    var intensity = 1 - Math.abs(y - intensityAreaHeight / 2) / (intensityAreaHeight / 2);
                    intensity = clamp(intensity, 0, 1);
                    var alpha = Math.round(intensity * 200);
                    ctx.fillStyle = 'rgba(' + rgb2.r + ',' + rgb2.g + ',' + rgb2.b + ',' + (alpha / 255) + ')';
                } else {
                    ctx.fillStyle = 'rgba(60, 60, 80, 0.3)';
                }
                ctx.fillRect(x2, intensityTop + y, 1, 1);
            }
        }

        var minPosX = ((allowedMin - totalMin) / (totalMax - totalMin)) * width;
        var maxPosX = ((allowedMax - totalMin) / (totalMax - totalMin)) * width;

        if (minPosX > 0) {
            var blockedGradLeft = ctx.createLinearGradient(0, 0, minPosX, 0);
            blockedGradLeft.addColorStop(0, 'rgba(10, 14, 23, 0.5)');
            blockedGradLeft.addColorStop(1, 'rgba(10, 14, 23, 0)');
            ctx.fillStyle = blockedGradLeft;
            ctx.fillRect(0, 0, minPosX, gradientAreaHeight);
        }

        if (maxPosX < width) {
            var blockedGradRight = ctx.createLinearGradient(maxPosX, 0, width, 0);
            blockedGradRight.addColorStop(0, 'rgba(10, 14, 23, 0)');
            blockedGradRight.addColorStop(1, 'rgba(10, 14, 23, 0.5)');
            ctx.fillStyle = blockedGradRight;
            ctx.fillRect(maxPosX, 0, width - maxPosX, gradientAreaHeight);
        }

        ctx.strokeStyle = 'rgba(0, 212, 255, 0.8)';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 3]);
        ctx.beginPath();
        ctx.moveTo(minPosX, 0);
        ctx.lineTo(minPosX, gradientAreaHeight);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(maxPosX, 0);
        ctx.lineTo(maxPosX, gradientAreaHeight);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = 'rgba(0, 212, 255, 0.9)';
        ctx.font = '10px monospace';
        ctx.textAlign = 'left';
        if (minPosX + 40 < width) {
            ctx.fillText(allowedMin + 'nm', minPosX + 4, gradientAreaHeight - 6);
        }
        ctx.textAlign = 'right';
        if (maxPosX - 40 > 0) {
            ctx.fillText(allowedMax + 'nm', maxPosX - 4, gradientAreaHeight - 6);
        }
    }

    function isWavelengthAccessible(wavelength) {
        return wavelength >= currentRange.min && wavelength <= currentRange.max;
    }

    function handleWavelengthCheck() {
        var inputEl = document.getElementById('wavelength-input');
        var resultEl = document.getElementById('wavelength-result');
        if (!inputEl || !resultEl) return;

        var wavelength = parseInt(inputEl.value, 10);
        if (isNaN(wavelength) || wavelength < 380 || wavelength > 780) {
            if (typeof App !== 'undefined' && App.showToast) {
                App.showToast('error', '无效波长', '请输入380-780范围内的有效波长');
            }
            return;
        }

        var rgb = wavelengthToRGB(wavelength);
        var hex = rgbToHex(rgb.r, rgb.g, rgb.b);
        var region = getWavelengthRegion(wavelength);
        var accessible = isWavelengthAccessible(wavelength);

        var colorBox = document.getElementById('wavelength-color');
        if (colorBox) {
            if (accessible) {
                colorBox.style.background = 'rgb(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ')';
                colorBox.style.boxShadow = '0 0 20px rgba(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ',0.5)';
                colorBox.style.opacity = '1';
            } else {
                var grayVal = Math.round((rgb.r + rgb.g + rgb.b) / 3 * 0.3 + 30);
                colorBox.style.background = 'rgb(' + grayVal + ',' + grayVal + ',' + grayVal + ')';
                colorBox.style.boxShadow = 'none';
                colorBox.style.opacity = '0.5';
            }
        }

        setTextContent('wl-value', String(wavelength));
        setTextContent('wl-region', region);
        setTextContent('wl-rgb', 'rgb(' + rgb.r + ', ' + rgb.g + ', ' + rgb.b + ')');
        setTextContent('wl-hex', hex);

        var accessEl = document.getElementById('wl-access');
        if (accessEl) {
            accessEl.textContent = '';
            if (accessible) {
                var okSpan = document.createElement('span');
                okSpan.style.color = 'var(--accent-green)';
                okSpan.style.fontWeight = '500';
                okSpan.textContent = '\u2713 允许访问 (当前等级可显示此波长)';
                accessEl.appendChild(okSpan);
            } else {
                var blockSpan = document.createElement('span');
                blockSpan.style.color = 'var(--accent-red)';
                blockSpan.style.fontWeight = '500';
                var reason = '';
                if (wavelength < currentRange.min) {
                    reason = '低于当前等级最小波长 ' + currentRange.min + 'nm';
                } else {
                    reason = '高于当前等级最大波长 ' + currentRange.max + 'nm';
                }
                blockSpan.textContent = '\u2717 访问受限 (' + reason + ')';
                accessEl.appendChild(blockSpan);
            }
        }

        resultEl.classList.remove('hidden');
    }

    function handleResize() {
        var info = detectResolutionLevel();
        updateDeviceInfoDisplay(info);
        drawSpectrumCanvas();
    }

    function initEvents() {
        var checkBtn = document.getElementById('wavelength-check-btn');
        if (checkBtn) {
            checkBtn.addEventListener('click', handleWavelengthCheck);
        }

        var wlInput = document.getElementById('wavelength-input');
        if (wlInput) {
            wlInput.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    handleWavelengthCheck();
                }
            });
        }

        var resizeTimer = null;
        window.addEventListener('resize', function () {
            if (resizeTimer) {
                clearTimeout(resizeTimer);
            }
            resizeTimer = setTimeout(handleResize, 150);
        });
    }

    function initDisplay() {
        var info = detectResolutionLevel();
        updateDeviceInfoDisplay(info);

        var canvas = document.getElementById('spectrum-canvas');
        if (canvas) {
            drawSpectrumCanvas();
        }
    }

    return {
        init: function () {
            initEvents();
            initDisplay();
        },
        refresh: function () {
            initDisplay();
        },
        getCurrentLevel: function () {
            return currentLevel;
        },
        getCurrentRange: function () {
            return { min: currentRange.min, max: currentRange.max };
        },
        isWavelengthAccessible: isWavelengthAccessible,
        wavelengthToRGB: wavelengthToRGB,
        wavelengthToRegion: getWavelengthRegion
    };
})();
