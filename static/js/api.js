'use strict';

const Api = (() => {
    async function request(method, url, body) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        const json = await res.json().catch(() => ({}));
        if (!res.ok) {
            const msg = json.error || json.message || `HTTP ${res.status}`;
            const err = new Error(msg);
            err.errorCode = json.error_code || null;
            err.httpStatus = res.status;
            throw err;
        }
        return json;
    }
    return {
        get:    (url)        => request('GET',    url),
        post:   (url, body)  => request('POST',   url, body),
        put:    (url, body)  => request('PUT',    url, body),
        delete: (url)        => request('DELETE', url),
    };
})();
