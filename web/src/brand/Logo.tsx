/** Two open pages whose negative space forms an "O", with a bookmark at the spine. */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg className="logo" width={size} height={size} viewBox="4 6 56 50" aria-hidden="true">
      <g fill="currentColor" fillRule="evenodd">
        <path d="M30.5 15.5C24.5 11 16 10.5 9 13v34c7-2 15.5-1 21.5 3.5V42a10 10 0 0 1 0-20z" />
        <path d="M33.5 15.5C39.500 11 48 10.500 55 13v34c-7-2-15.500-1-21.500 3.500V42a10 10 0 0 0 0-20z" />
      </g>
      <path className="logo-bookmark" d="M43 9.500h6.500v15l-3.250-3-3.250 3z" />
    </svg>
  );
}
