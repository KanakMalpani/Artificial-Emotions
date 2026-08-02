/**
 * Mount contract: features/stances
 * - ComparePanel — profile / constitution compare
 * - StanceNav / StanceLensList — C2 seven-lens primary nav
 */
export { ComparePanel } from "./ComparePanel";
export type { ComparePanelProps } from "./ComparePanel";
export { StanceNav } from "./StanceNav";
export type { StanceNavProps } from "./StanceNav";
export { StanceLensList } from "./StanceLensList";
export type { StanceLensListProps } from "./StanceLensList";
export {
  STANCE_IDS,
  STANCE_META,
  applyLens,
  type StanceId,
  type LensResult,
} from "./lenses";
