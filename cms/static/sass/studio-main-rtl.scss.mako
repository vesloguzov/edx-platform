// studio - css architecture
// ====================

// Table of Contents
// * +Libs and Resets
// * +Vendor and Rebase
// * +Base - Utilities
// * +Base - Assets
// * +Base - Starter
// * +Base - Elements
// * +Base - Specific Views
// * +Base - Contexts
// * +Xmodule

// +Libs and Resets - *do not edit*
// ====================
@import 'bourbon/bourbon'; // lib - bourbon
@import 'vendor/bi-app/bi-app-rtl'; // set the layout for right to left languages

// +Vendor and Rebase - *referenced/used vendor presentation and reset*
// ====================
@import 'reset';

// +Base - Utilities
// ====================
@import 'variables';
@import 'mixins';
@import 'mixins-inherited';

% if env["FEATURES"].get("USE_CUSTOM_STUDIO_THEME", False):
  // import theme's Sass overrides
  @import '${env.get('STUDIO_THEME_NAME')}';
% endif

@import 'build'; // shared app style assets/rendering
