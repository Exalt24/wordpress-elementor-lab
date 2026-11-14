<?php
namespace Bullion;

final class Headers
{
    /** Response headers sent on every page WordPress serves. HSTS goes only on an HTTPS reply, because a browser that sees it on http would be locked out of a site that has no certificate. */
    public static function security(bool $https): array
    {
        $h = [
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'SAMEORIGIN',
            'Referrer-Policy' => 'strict-origin-when-cross-origin',
            'Permissions-Policy' => 'geolocation=(), microphone=(), camera=()',
        ];
        if ($https) {
            $h['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains';
        }
        return $h;
    }
}
