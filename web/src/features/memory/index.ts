/**
 * Mount contract: features/memory
 * - TrajectoryMap — C3 path visualization
 * - ConfessionPanel — C5 honesty / avoidance / claims_not
 */
export { TrajectoryMap } from "./TrajectoryMap";
export type { TrajectoryMapProps } from "./TrajectoryMap";
export { ConfessionPanel } from "./ConfessionPanel";
export type { ConfessionPanelProps } from "./ConfessionPanel";
export {
  DEMO_TRAJECTORY,
  sketchFromResults,
  type TrajectoryView,
} from "./trajectoryTypes";
/** @deprecated Use TrajectoryMap — stub kept for mount compatibility */
export { TrajectoryMap as MemoryStub } from "./TrajectoryMap";
