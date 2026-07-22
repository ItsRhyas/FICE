/* FICE dashboard charts — Chart.js integration. */

(function () {
    const currencySymbols = {
        USD: '$',
        NIO: 'C$',
    };

    function formatMoney(valueInCents) {
        return (valueInCents / 100).toFixed(2);
    }

    function commonOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.parsed.y !== undefined
                                ? context.parsed.y
                                : context.parsed;
                            return `${context.dataset.label || ''}: ${formatMoney(value)}`;
                        },
                    },
                },
            },
        };
    }

    async function initMonthlySummaryChart() {
        const canvas = document.getElementById('monthly-summary-chart');
        if (!canvas) return;

        const response = await fetch('/api/charts/monthly-summary');
        const data = await response.json();

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map((item) => item.month),
                datasets: [
                    {
                        label: 'Ingresos',
                        data: data.map((item) => item.income),
                        backgroundColor: 'rgba(34, 197, 94, 0.7)',
                        borderColor: 'rgba(34, 197, 94, 1)',
                        borderWidth: 1,
                    },
                    {
                        label: 'Egresos',
                        data: data.map((item) => item.expense),
                        backgroundColor: 'rgba(239, 68, 68, 0.7)',
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 1,
                    },
                ],
            },
            options: commonOptions('Ingresos vs egresos'),
        });
    }

    async function initBalanceDistributionChart() {
        const canvas = document.getElementById('balance-distribution-chart');
        if (!canvas) return;

        const response = await fetch('/api/charts/balance-distribution');
        const data = await response.json();

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: data.map((item) => `${item.label} (${item.currency})`),
                datasets: [
                    {
                        data: data.map((item) => item.balance),
                        backgroundColor: [
                            'rgba(37, 99, 235, 0.7)',
                            'rgba(16, 185, 129, 0.7)',
                            'rgba(245, 158, 11, 0.7)',
                            'rgba(139, 92, 246, 0.7)',
                            'rgba(236, 72, 153, 0.7)',
                            'rgba(6, 182, 212, 0.7)',
                        ],
                        borderColor: 'rgba(0, 0, 0, 0.1)',
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = data[context.dataIndex];
                                return `${item.label}: ${currencySymbols[item.currency] || item.currency} ${formatMoney(item.balance)}`;
                            },
                        },
                    },
                },
            },
        });
    }

    async function initNetWorthTrendChart() {
        const canvas = document.getElementById('net-worth-trend-chart');
        if (!canvas) return;

        const response = await fetch('/api/charts/net-worth-trend');
        const data = await response.json();

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.map((item) => item.date),
                datasets: [
                    {
                        label: 'USD',
                        data: data.map((item) => item.USD),
                        borderColor: 'rgba(37, 99, 235, 1)',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        fill: false,
                        tension: 0.2,
                    },
                    {
                        label: 'NIO',
                        data: data.map((item) => item.NIO),
                        borderColor: 'rgba(245, 158, 11, 1)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        fill: false,
                        tension: 0.2,
                    },
                ],
            },
            options: commonOptions('Evolución del patrimonio'),
        });
    }

    function initCharts() {
        initMonthlySummaryChart();
        initBalanceDistributionChart();
        initNetWorthTrendChart();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCharts);
    } else {
        initCharts();
    }
})();
