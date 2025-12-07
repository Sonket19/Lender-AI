import { useAuth } from '@/components/auth-provider';

export async function getAuthHeaders(): Promise<HeadersInit> {
    // This function should be called from components that have access to useAuth
    // For now, we'll get the token directly from Firebase
    const { auth } = await import('@/lib/firebase');
    const user = auth.currentUser;

    if (!user) {
        return {};
    }

    try {
        const token = await user.getIdToken();
        return {
            'Authorization': `Bearer ${token}`,
        };
    } catch (error) {
        console.error('Error getting auth token:', error);
        return {};
    }
}

export async function authenticatedFetch(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    const authHeaders = await getAuthHeaders();

    const headers = new Headers(options.headers);
    Object.entries(authHeaders).forEach(([key, value]) => {
        headers.set(key, value);
    });

    return fetch(url, {
        ...options,
        headers,
    });
}
