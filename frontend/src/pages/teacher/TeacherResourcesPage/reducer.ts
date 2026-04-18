import type { ResourcePageState, ResourcePageAction } from './types';

export const initialState: ResourcePageState = {
  searchTerm: '',
  selectedType: 'all',
  viewMode: 'grid',
  deleteConfirmId: null,
  viewingResource: null,
  selectionMode: false,
  selectedResourceIds: new Set(),
  showBatchDeleteConfirm: false,
  editingResource: null,
  showBatchImportModal: false,
};

export const resourcePageReducer = (
  state: ResourcePageState,
  action: ResourcePageAction
): ResourcePageState => {
  switch (action.type) {
    case 'SET_SEARCH_TERM':
      return { ...state, searchTerm: action.payload };

    case 'SET_SELECTED_TYPE':
      return { ...state, selectedType: action.payload };

    case 'SET_VIEW_MODE':
      return { ...state, viewMode: action.payload };

    case 'OPEN_DELETE_CONFIRM':
      return { ...state, deleteConfirmId: action.payload };

    case 'CLOSE_DELETE_CONFIRM':
      return { ...state, deleteConfirmId: null };

    case 'SET_VIEWING_RESOURCE':
      return { ...state, viewingResource: action.payload };

    case 'CLOSE_VIEWING_RESOURCE':
      return { ...state, viewingResource: null };

    case 'TOGGLE_SELECTION_MODE':
      return {
        ...state,
        selectionMode: !state.selectionMode,
        selectedResourceIds: state.selectionMode ? new Set() : state.selectedResourceIds,
      };

    case 'EXIT_SELECTION_MODE':
      return { ...state, selectionMode: false };

    case 'TOGGLE_RESOURCE_SELECTION': {
      const next = new Set(state.selectedResourceIds);
      if (next.has(action.payload)) {
        next.delete(action.payload);
      } else {
        next.add(action.payload);
      }
      return { ...state, selectedResourceIds: next };
    }

    case 'SELECT_ALL':
      return { ...state, selectedResourceIds: new Set(action.payload) };

    case 'CLEAR_SELECTION':
      return { ...state, selectedResourceIds: new Set() };

    case 'OPEN_BATCH_DELETE_CONFIRM':
      return { ...state, showBatchDeleteConfirm: true };

    case 'CLOSE_BATCH_DELETE_CONFIRM':
      return { ...state, showBatchDeleteConfirm: false };

    case 'OPEN_EDIT':
      return { ...state, editingResource: action.payload };

    case 'CLOSE_EDIT':
      return { ...state, editingResource: null };

    case 'OPEN_BATCH_IMPORT':
      return { ...state, showBatchImportModal: true };

    case 'CLOSE_BATCH_IMPORT':
      return { ...state, showBatchImportModal: false };

    default:
      return state;
  }
};
