function Skeleton({ className = '', style }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`.trim()} style={style} />;
}

export default Skeleton;

