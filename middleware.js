import { NextResponse } from 'next/server';

export function middleware(request) {
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith('/api/') ||
    pathname === '/login.html' ||
    pathname === '/favicon.ico' ||
    pathname.startsWith('/_next/')
  ) {
    return NextResponse.next();
  }

  const expected = process.env.ACCESS_KEY;
  const token = request.cookies.get('lc_access')?.value;

  if (expected && token === expected) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = '/login.html';
  url.searchParams.set('next', pathname || '/');
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image).*)'],
};
