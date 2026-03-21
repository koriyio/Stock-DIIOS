const api = {
    async getRangos() {
        try {
            const res = await fetch('/api/rangos');
            if (!res.ok) return [];
            return await res.json();
        } catch { return []; }
    },
    async saveRangos(rangos) {
        try {
            await fetch('/api/rangos/bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rangos)
            });
        } catch (e) {
            console.error('Error saving rangos:', e);
        }
    },
    async getFuncionarios() {
        try {
            const res = await fetch('/api/funcionarios');
            if (!res.ok) return [];
            return await res.json();
        } catch { return []; }
    },
    async saveFuncionarios(funcionarios) {
        try {
            await fetch('/api/funcionarios/bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(funcionarios)
            });
        } catch (e) {
            console.error('Error saving funcionarios:', e);
        }
    },
    async getHistorial() {
        try {
            const res = await fetch('/api/historial');
            if (!res.ok) return [];
            return await res.json();
        } catch { return []; }
    },
    async saveHistorial(historial) {
        try {
            await fetch('/api/historial/bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(historial)
            });
        } catch (e) {
            console.error('Error saving historial:', e);
        }
    }
};

window.api = api;
