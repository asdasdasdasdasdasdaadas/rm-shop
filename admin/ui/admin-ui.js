function KS(a, u) {
  for (var r = 0; r < u.length; r++) {
    const c = u[r];
    if (typeof c != "string" && !Array.isArray(c)) {
      for (const f in c)
        if (f !== "default" && !(f in a)) {
          const m = Object.getOwnPropertyDescriptor(c, f);
          m && Object.defineProperty(a, f, m.get ? m : {
            enumerable: !0,
            get: () => c[f]
          });
        }
    }
  }
  return Object.freeze(Object.defineProperty(a, Symbol.toStringTag, { value: "Module" }));
}
function ty(a) {
  return a && a.__esModule && Object.prototype.hasOwnProperty.call(a, "default") ? a.default : a;
}
var Rf = { exports: {} }, Lo = {};
/**
 * @license React
 * react-jsx-runtime.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var i0;
function JS() {
  if (i0) return Lo;
  i0 = 1;
  var a = Symbol.for("react.transitional.element"), u = Symbol.for("react.fragment");
  function r(c, f, m) {
    var v = null;
    if (m !== void 0 && (v = "" + m), f.key !== void 0 && (v = "" + f.key), "key" in f) {
      m = {};
      for (var g in f)
        g !== "key" && (m[g] = f[g]);
    } else m = f;
    return f = m.ref, {
      $$typeof: a,
      type: c,
      key: v,
      ref: f !== void 0 ? f : null,
      props: m
    };
  }
  return Lo.Fragment = u, Lo.jsx = r, Lo.jsxs = r, Lo;
}
var o0;
function FS() {
  return o0 || (o0 = 1, Rf.exports = JS()), Rf.exports;
}
var k = FS(), Nf = { exports: {} }, Et = {};
/**
 * @license React
 * react.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var u0;
function $S() {
  if (u0) return Et;
  u0 = 1;
  var a = Symbol.for("react.transitional.element"), u = Symbol.for("react.portal"), r = Symbol.for("react.fragment"), c = Symbol.for("react.strict_mode"), f = Symbol.for("react.profiler"), m = Symbol.for("react.consumer"), v = Symbol.for("react.context"), g = Symbol.for("react.forward_ref"), p = Symbol.for("react.suspense"), y = Symbol.for("react.memo"), S = Symbol.for("react.lazy"), d = Symbol.for("react.activity"), x = Symbol.for("react.view_transition"), C = Symbol.iterator;
  function R(E) {
    return E === null || typeof E != "object" ? null : (E = C && E[C] || E["@@iterator"], typeof E == "function" ? E : null);
  }
  var O = {
    isMounted: function() {
      return !1;
    },
    enqueueForceUpdate: function() {
    },
    enqueueReplaceState: function() {
    },
    enqueueSetState: function() {
    }
  }, N = Object.assign, H = {};
  function L(E, _, V) {
    this.props = E, this.context = _, this.refs = H, this.updater = V || O;
  }
  L.prototype.isReactComponent = {}, L.prototype.setState = function(E, _) {
    if (typeof E != "object" && typeof E != "function" && E != null)
      throw Error(
        "takes an object of state variables to update or a function which returns an object of state variables."
      );
    this.updater.enqueueSetState(this, E, _, "setState");
  }, L.prototype.forceUpdate = function(E) {
    this.updater.enqueueForceUpdate(this, E, "forceUpdate");
  };
  function J() {
  }
  J.prototype = L.prototype;
  function K(E, _, V) {
    this.props = E, this.context = _, this.refs = H, this.updater = V || O;
  }
  var I = K.prototype = new J();
  I.constructor = K, N(I, L.prototype), I.isPureReactComponent = !0;
  var Z = Array.isArray;
  function X() {
  }
  var Y = { H: null, A: null, T: null, S: null }, dt = Object.prototype.hasOwnProperty;
  function ht(E, _, V) {
    var $ = V.ref;
    return {
      $$typeof: a,
      type: E,
      key: _,
      ref: $ !== void 0 ? $ : null,
      props: V
    };
  }
  function xt(E, _) {
    return ht(E.type, _, E.props);
  }
  function st(E) {
    return typeof E == "object" && E !== null && E.$$typeof === a;
  }
  function Tt(E) {
    var _ = { "=": "=0", ":": "=2" };
    return "$" + E.replace(/[=:]/g, function(V) {
      return _[V];
    });
  }
  var gt = /\/+/g;
  function yt(E, _) {
    return typeof E == "object" && E !== null && E.key != null ? Tt("" + E.key) : _.toString(36);
  }
  function B(E) {
    switch (E.status) {
      case "fulfilled":
        return E.value;
      case "rejected":
        throw E.reason;
      default:
        switch (typeof E.status == "string" ? E.then(X, X) : (E.status = "pending", E.then(
          function(_) {
            E.status === "pending" && (E.status = "fulfilled", E.value = _);
          },
          function(_) {
            E.status === "pending" && (E.status = "rejected", E.reason = _);
          }
        )), E.status) {
          case "fulfilled":
            return E.value;
          case "rejected":
            throw E.reason;
        }
    }
    throw E;
  }
  function tt(E, _, V, $, ft) {
    var W = typeof E;
    (W === "undefined" || W === "boolean") && (E = null);
    var bt = !1;
    if (E === null) bt = !0;
    else
      switch (W) {
        case "bigint":
        case "string":
        case "number":
          bt = !0;
          break;
        case "object":
          switch (E.$$typeof) {
            case a:
            case u:
              bt = !0;
              break;
            case S:
              return bt = E._init, tt(
                bt(E._payload),
                _,
                V,
                $,
                ft
              );
          }
      }
    if (bt)
      return ft = ft(E), bt = $ === "" ? "." + yt(E, 0) : $, Z(ft) ? (V = "", bt != null && (V = bt.replace(gt, "$&/") + "/"), tt(ft, _, V, "", function(It) {
        return It;
      })) : ft != null && (st(ft) && (ft = xt(
        ft,
        V + (ft.key == null || E && E.key === ft.key ? "" : ("" + ft.key).replace(
          gt,
          "$&/"
        ) + "/") + bt
      )), _.push(ft)), 1;
    bt = 0;
    var lt = $ === "" ? "." : $ + ":";
    if (Z(E))
      for (var mt = 0; mt < E.length; mt++)
        $ = E[mt], W = lt + yt($, mt), bt += tt(
          $,
          _,
          V,
          W,
          ft
        );
    else if (mt = R(E), typeof mt == "function")
      for (E = mt.call(E), mt = 0; !($ = E.next()).done; )
        $ = $.value, W = lt + yt($, mt++), bt += tt(
          $,
          _,
          V,
          W,
          ft
        );
    else if (W === "object") {
      if (typeof E.then == "function")
        return tt(
          B(E),
          _,
          V,
          $,
          ft
        );
      throw _ = String(E), Error(
        "Objects are not valid as a React child (found: " + (_ === "[object Object]" ? "object with keys {" + Object.keys(E).join(", ") + "}" : _) + "). If you meant to render a collection of children, use an array instead."
      );
    }
    return bt;
  }
  function P(E, _, V) {
    if (E == null) return E;
    var $ = [], ft = 0;
    return tt(E, $, "", "", function(W) {
      return _.call(V, W, ft++);
    }), $;
  }
  function at(E) {
    if (E._status === -1) {
      var _ = E._result, V = _();
      V.then(
        function($) {
          (E._status === 0 || E._status === -1) && (E._status = 1, E._result = $, V.status === void 0 && (V.status = "fulfilled", V.value = $));
        },
        function($) {
          (E._status === 0 || E._status === -1) && (E._status = 2, E._result = $, V.status === void 0 && (V.status = "rejected", V.reason = $));
        }
      ), E._status === -1 && (E._status = 0, E._result = V);
    }
    if (E._status === 1) return E._result.default;
    throw E._result;
  }
  var F = typeof reportError == "function" ? reportError : function(E) {
    if (typeof window == "object" && typeof window.ErrorEvent == "function") {
      var _ = new window.ErrorEvent("error", {
        bubbles: !0,
        cancelable: !0,
        message: typeof E == "object" && E !== null && typeof E.message == "string" ? String(E.message) : String(E),
        error: E
      });
      if (!window.dispatchEvent(_)) return;
    } else if (typeof process == "object" && typeof process.emit == "function") {
      process.emit("uncaughtException", E);
      return;
    }
    console.error(E);
  };
  function Bt(E) {
    var _ = Y.T, V = {};
    V.types = _ !== null ? _.types : null, Y.T = V;
    try {
      var $ = E(), ft = Y.S;
      ft !== null && ft(V, $), typeof $ == "object" && $ !== null && typeof $.then == "function" && $.then(X, F);
    } catch (W) {
      F(W);
    } finally {
      _ !== null && V.types !== null && (_.types = V.types), Y.T = _;
    }
  }
  function Q(E) {
    var _ = Y.T;
    if (_ !== null) {
      var V = _.types;
      V === null ? _.types = [E] : V.indexOf(E) === -1 && V.push(E);
    } else Bt(Q.bind(null, E));
  }
  var rt = {
    map: P,
    forEach: function(E, _, V) {
      P(
        E,
        function() {
          _.apply(this, arguments);
        },
        V
      );
    },
    count: function(E) {
      var _ = 0;
      return P(E, function() {
        _++;
      }), _;
    },
    toArray: function(E) {
      return P(E, function(_) {
        return _;
      }) || [];
    },
    only: function(E) {
      if (!st(E))
        throw Error(
          "React.Children.only expected to receive a single React element child."
        );
      return E;
    }
  };
  return Et.Activity = d, Et.Children = rt, Et.Component = L, Et.Fragment = r, Et.Profiler = f, Et.PureComponent = K, Et.StrictMode = c, Et.Suspense = p, Et.ViewTransition = x, Et.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = Y, Et.__COMPILER_RUNTIME = {
    __proto__: null,
    c: function(E) {
      return Y.H.useMemoCache(E);
    }
  }, Et.addTransitionType = Q, Et.cache = function(E) {
    return function() {
      return E.apply(null, arguments);
    };
  }, Et.cacheSignal = function() {
    return null;
  }, Et.cloneElement = function(E, _, V) {
    if (E == null)
      throw Error(
        "The argument must be a React element, but you passed " + E + "."
      );
    var $ = N({}, E.props), ft = E.key;
    if (_ != null)
      for (W in _.key !== void 0 && (ft = "" + _.key), _)
        !dt.call(_, W) || W === "key" || W === "__self" || W === "__source" || W === "ref" && _.ref === void 0 || ($[W] = _[W]);
    var W = arguments.length - 2;
    if (W === 1) $.children = V;
    else if (1 < W) {
      for (var bt = Array(W), lt = 0; lt < W; lt++)
        bt[lt] = arguments[lt + 2];
      $.children = bt;
    }
    return ht(E.type, ft, $);
  }, Et.createContext = function(E) {
    return E = {
      $$typeof: v,
      _currentValue: E,
      _currentValue2: E,
      _threadCount: 0,
      Provider: null,
      Consumer: null
    }, E.Provider = E, E.Consumer = {
      $$typeof: m,
      _context: E
    }, E;
  }, Et.createElement = function(E, _, V) {
    var $, ft = {}, W = null;
    if (_ != null)
      for ($ in _.key !== void 0 && (W = "" + _.key), _)
        dt.call(_, $) && $ !== "key" && $ !== "__self" && $ !== "__source" && (ft[$] = _[$]);
    var bt = arguments.length - 2;
    if (bt === 1) ft.children = V;
    else if (1 < bt) {
      for (var lt = Array(bt), mt = 0; mt < bt; mt++)
        lt[mt] = arguments[mt + 2];
      ft.children = lt;
    }
    if (E && E.defaultProps)
      for ($ in bt = E.defaultProps, bt)
        ft[$] === void 0 && (ft[$] = bt[$]);
    return ht(E, W, ft);
  }, Et.createRef = function() {
    return { current: null };
  }, Et.forwardRef = function(E) {
    return { $$typeof: g, render: E };
  }, Et.isValidElement = st, Et.lazy = function(E) {
    return {
      $$typeof: S,
      _payload: { _status: -1, _result: E },
      _init: at
    };
  }, Et.memo = function(E, _) {
    return {
      $$typeof: y,
      type: E,
      compare: _ === void 0 ? null : _
    };
  }, Et.startTransition = Bt, Et.unstable_useCacheRefresh = function() {
    return Y.H.useCacheRefresh();
  }, Et.use = function(E) {
    return Y.H.use(E);
  }, Et.useActionState = function(E, _, V) {
    return Y.H.useActionState(E, _, V);
  }, Et.useCallback = function(E, _) {
    return Y.H.useCallback(E, _);
  }, Et.useContext = function(E) {
    return Y.H.useContext(E);
  }, Et.useDebugValue = function() {
  }, Et.useDeferredValue = function(E, _) {
    return Y.H.useDeferredValue(E, _);
  }, Et.useEffect = function(E, _) {
    return Y.H.useEffect(E, _);
  }, Et.useEffectEvent = function(E) {
    return Y.H.useEffectEvent(E);
  }, Et.useId = function() {
    return Y.H.useId();
  }, Et.useImperativeHandle = function(E, _, V) {
    return Y.H.useImperativeHandle(E, _, V);
  }, Et.useInsertionEffect = function(E, _) {
    return Y.H.useInsertionEffect(E, _);
  }, Et.useLayoutEffect = function(E, _) {
    return Y.H.useLayoutEffect(E, _);
  }, Et.useMemo = function(E, _) {
    return Y.H.useMemo(E, _);
  }, Et.useOptimistic = function(E, _) {
    return Y.H.useOptimistic(E, _);
  }, Et.useReducer = function(E, _, V) {
    return Y.H.useReducer(E, _, V);
  }, Et.useRef = function(E) {
    return Y.H.useRef(E);
  }, Et.useState = function(E) {
    return Y.H.useState(E);
  }, Et.useSyncExternalStore = function(E, _, V) {
    return Y.H.useSyncExternalStore(
      E,
      _,
      V
    );
  }, Et.useTransition = function() {
    return Y.H.useTransition();
  }, Et.version = "19.3.0", Et;
}
var r0;
function dd() {
  return r0 || (r0 = 1, Nf.exports = $S()), Nf.exports;
}
var b = dd();
const et = /* @__PURE__ */ ty(b), Ko = /* @__PURE__ */ KS({
  __proto__: null,
  default: et
}, [b]);
var Df = { exports: {} }, Yo = {}, zf = { exports: {} }, Mf = {};
/**
 * @license React
 * scheduler.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var c0;
function IS() {
  return c0 || (c0 = 1, (function(a) {
    function u(B, tt) {
      var P = B.length;
      B.push(tt);
      t: for (; 0 < P; ) {
        var at = P - 1 >>> 1, F = B[at];
        if (0 < f(F, tt))
          B[at] = tt, B[P] = F, P = at;
        else break t;
      }
    }
    function r(B) {
      return B.length === 0 ? null : B[0];
    }
    function c(B) {
      if (B.length === 0) return null;
      var tt = B[0], P = B.pop();
      if (P !== tt) {
        B[0] = P;
        t: for (var at = 0, F = B.length, Bt = F >>> 1; at < Bt; ) {
          var Q = 2 * (at + 1) - 1, rt = B[Q], E = Q + 1, _ = B[E];
          if (0 > f(rt, P))
            E < F && 0 > f(_, rt) ? (B[at] = _, B[E] = P, at = E) : (B[at] = rt, B[Q] = P, at = Q);
          else if (E < F && 0 > f(_, P))
            B[at] = _, B[E] = P, at = E;
          else break t;
        }
      }
      return tt;
    }
    function f(B, tt) {
      var P = B.sortIndex - tt.sortIndex;
      return P !== 0 ? P : B.id - tt.id;
    }
    if (a.unstable_now = void 0, typeof performance == "object" && typeof performance.now == "function") {
      var m = performance;
      a.unstable_now = function() {
        return m.now();
      };
    } else {
      var v = Date, g = v.now();
      a.unstable_now = function() {
        return v.now() - g;
      };
    }
    var p = [], y = [], S = 1, d = null, x = 3, C = !1, R = !1, O = !1, N = !1, H = typeof setTimeout == "function" ? setTimeout : null, L = typeof clearTimeout == "function" ? clearTimeout : null, J = typeof setImmediate < "u" ? setImmediate : null;
    function K(B) {
      for (var tt = r(y); tt !== null; ) {
        if (tt.callback === null) c(y);
        else if (tt.startTime <= B)
          c(y), tt.sortIndex = tt.expirationTime, u(p, tt);
        else break;
        tt = r(y);
      }
    }
    function I(B) {
      if (O = !1, K(B), !R)
        if (r(p) !== null)
          R = !0, Z || (Z = !0, st());
        else {
          var tt = r(y);
          tt !== null && yt(I, tt.startTime - B);
        }
    }
    var Z = !1, X = -1, Y = 5, dt = -1;
    function ht() {
      return N ? !0 : !(a.unstable_now() - dt < Y);
    }
    function xt() {
      if (N = !1, Z) {
        var B = a.unstable_now();
        dt = B;
        var tt = !0;
        try {
          t: {
            R = !1, O && (O = !1, L(X), X = -1), C = !0;
            var P = x;
            try {
              e: {
                for (K(B), d = r(p); d !== null && !(d.expirationTime > B && ht()); ) {
                  var at = d.callback;
                  if (typeof at == "function") {
                    d.callback = null, x = d.priorityLevel;
                    var F = at(
                      d.expirationTime <= B
                    );
                    if (B = a.unstable_now(), typeof F == "function") {
                      d.callback = F, K(B), tt = !0;
                      break e;
                    }
                    d === r(p) && c(p), K(B);
                  } else c(p);
                  d = r(p);
                }
                if (d !== null) tt = !0;
                else {
                  var Bt = r(y);
                  Bt !== null && yt(
                    I,
                    Bt.startTime - B
                  ), tt = !1;
                }
              }
              break t;
            } finally {
              d = null, x = P, C = !1;
            }
            tt = void 0;
          }
        } finally {
          tt ? st() : Z = !1;
        }
      }
    }
    var st;
    if (typeof J == "function")
      st = function() {
        J(xt);
      };
    else if (typeof MessageChannel < "u") {
      var Tt = new MessageChannel(), gt = Tt.port2;
      Tt.port1.onmessage = xt, st = function() {
        gt.postMessage(null);
      };
    } else
      st = function() {
        H(xt, 0);
      };
    function yt(B, tt) {
      X = H(function() {
        B(a.unstable_now());
      }, tt);
    }
    a.unstable_IdlePriority = 5, a.unstable_ImmediatePriority = 1, a.unstable_LowPriority = 4, a.unstable_NormalPriority = 3, a.unstable_Profiling = null, a.unstable_UserBlockingPriority = 2, a.unstable_cancelCallback = function(B) {
      B.callback = null;
    }, a.unstable_forceFrameRate = function(B) {
      0 > B || 125 < B ? console.error(
        "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"
      ) : Y = 0 < B ? Math.floor(1e3 / B) : 5;
    }, a.unstable_getCurrentPriorityLevel = function() {
      return x;
    }, a.unstable_next = function(B) {
      switch (x) {
        case 1:
        case 2:
        case 3:
          var tt = 3;
          break;
        default:
          tt = x;
      }
      var P = x;
      x = tt;
      try {
        return B();
      } finally {
        x = P;
      }
    }, a.unstable_requestPaint = function() {
      N = !0;
    }, a.unstable_runWithPriority = function(B, tt) {
      switch (B) {
        case 1:
        case 2:
        case 3:
        case 4:
        case 5:
          break;
        default:
          B = 3;
      }
      var P = x;
      x = B;
      try {
        return tt();
      } finally {
        x = P;
      }
    }, a.unstable_scheduleCallback = function(B, tt, P) {
      var at = a.unstable_now();
      switch (typeof P == "object" && P !== null ? (P = P.delay, P = typeof P == "number" && 0 < P ? at + P : at) : P = at, B) {
        case 1:
          var F = -1;
          break;
        case 2:
          F = 250;
          break;
        case 5:
          F = 1073741823;
          break;
        case 4:
          F = 1e4;
          break;
        default:
          F = 5e3;
      }
      return F = P + F, B = {
        id: S++,
        callback: tt,
        priorityLevel: B,
        startTime: P,
        expirationTime: F,
        sortIndex: -1
      }, P > at ? (B.sortIndex = P, u(y, B), r(p) === null && B === r(y) && (O ? (L(X), X = -1) : O = !0, yt(I, P - at))) : (B.sortIndex = F, u(p, B), R || C || (R = !0, Z || (Z = !0, st()))), B;
    }, a.unstable_shouldYield = ht, a.unstable_wrapCallback = function(B) {
      var tt = x;
      return function() {
        var P = x;
        x = tt;
        try {
          return B.apply(this, arguments);
        } finally {
          x = P;
        }
      };
    };
  })(Mf)), Mf;
}
var s0;
function PS() {
  return s0 || (s0 = 1, zf.exports = IS()), zf.exports;
}
var Uf = { exports: {} }, we = {};
/**
 * @license React
 * react-dom.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var f0;
function WS() {
  if (f0) return we;
  f0 = 1;
  var a = dd();
  function u(S) {
    var d = "https://react.dev/errors/" + S;
    if (1 < arguments.length) {
      d += "?args[]=" + encodeURIComponent(arguments[1]);
      for (var x = 2; x < arguments.length; x++)
        d += "&args[]=" + encodeURIComponent(arguments[x]);
    }
    return "Minified React error #" + S + "; visit " + d + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
  }
  function r() {
  }
  var c = {
    d: {
      f: r,
      r: function() {
        throw Error(u(522));
      },
      D: r,
      C: r,
      L: r,
      m: r,
      X: r,
      S: r,
      M: r
    },
    p: 0,
    findDOMNode: null
  }, f = Symbol.for("react.portal"), m = Symbol.for("react.recoverable"), v = Symbol.for("react.optimistic_key");
  function g(S, d, x) {
    var C = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
    return {
      $$typeof: f,
      key: C == null ? null : C === v ? v : "" + C,
      children: S,
      containerInfo: d,
      implementation: x
    };
  }
  var p = a.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
  function y(S, d) {
    if (S === "font") return "";
    if (typeof d == "string")
      return d === "use-credentials" ? d : "";
  }
  return we.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = c, we.browser = function(S) {
    return { $$typeof: m, _reason: S };
  }, we.createPortal = function(S, d) {
    var x = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
    if (!d || d.nodeType !== 1 && d.nodeType !== 9 && d.nodeType !== 11)
      throw Error(u(299));
    return g(S, d, null, x);
  }, we.flushSync = function(S) {
    var d = p.T, x = c.p;
    try {
      if (p.T = null, c.p = 2, S) return S();
    } finally {
      p.T = d, c.p = x, c.d.f();
    }
  }, we.preconnect = function(S, d) {
    typeof S == "string" && (d ? (d = d.crossOrigin, d = typeof d == "string" ? d === "use-credentials" ? d : "" : void 0) : d = null, c.d.C(S, d));
  }, we.prefetchDNS = function(S) {
    typeof S == "string" && c.d.D(S);
  }, we.preinit = function(S, d) {
    if (typeof S == "string" && d && typeof d.as == "string") {
      var x = d.as, C = y(x, d.crossOrigin), R = typeof d.integrity == "string" ? d.integrity : void 0, O = typeof d.fetchPriority == "string" ? d.fetchPriority : void 0;
      x === "style" ? c.d.S(
        S,
        typeof d.precedence == "string" ? d.precedence : void 0,
        {
          crossOrigin: C,
          integrity: R,
          fetchPriority: O
        }
      ) : x === "script" && c.d.X(S, {
        crossOrigin: C,
        integrity: R,
        fetchPriority: O,
        nonce: typeof d.nonce == "string" ? d.nonce : void 0
      });
    }
  }, we.preinitModule = function(S, d) {
    if (typeof S == "string")
      if (typeof d == "object" && d !== null) {
        if (d.as == null || d.as === "script") {
          var x = y(
            d.as,
            d.crossOrigin
          );
          c.d.M(S, {
            crossOrigin: x,
            integrity: typeof d.integrity == "string" ? d.integrity : void 0,
            nonce: typeof d.nonce == "string" ? d.nonce : void 0,
            fetchPriority: typeof d.fetchPriority == "string" ? d.fetchPriority : void 0
          });
        }
      } else d == null && c.d.M(S);
  }, we.preload = function(S, d) {
    if (typeof S == "string" && typeof d == "object" && d !== null && typeof d.as == "string") {
      var x = d.as, C = y(x, d.crossOrigin);
      c.d.L(S, x, {
        crossOrigin: C,
        integrity: typeof d.integrity == "string" ? d.integrity : void 0,
        nonce: typeof d.nonce == "string" ? d.nonce : void 0,
        type: typeof d.type == "string" ? d.type : void 0,
        fetchPriority: typeof d.fetchPriority == "string" ? d.fetchPriority : void 0,
        referrerPolicy: typeof d.referrerPolicy == "string" ? d.referrerPolicy : void 0,
        imageSrcSet: typeof d.imageSrcSet == "string" ? d.imageSrcSet : void 0,
        imageSizes: typeof d.imageSizes == "string" ? d.imageSizes : void 0,
        media: typeof d.media == "string" ? d.media : void 0
      });
    }
  }, we.preloadModule = function(S, d) {
    if (typeof S == "string")
      if (d) {
        var x = y(d.as, d.crossOrigin);
        c.d.m(S, {
          as: typeof d.as == "string" && d.as !== "script" ? d.as : void 0,
          crossOrigin: x,
          integrity: typeof d.integrity == "string" ? d.integrity : void 0,
          nonce: typeof d.nonce == "string" ? d.nonce : void 0,
          fetchPriority: typeof d.fetchPriority == "string" ? d.fetchPriority : void 0
        });
      } else c.d.m(S);
  }, we.requestFormReset = function(S) {
    c.d.r(S);
  }, we.unstable_batchedUpdates = function(S, d) {
    return S(d);
  }, we.useFormState = function(S, d, x) {
    return p.H.useFormState(S, d, x);
  }, we.useFormStatus = function() {
    return p.H.useHostTransitionStatus();
  }, we.version = "19.3.0", we;
}
var d0;
function ey() {
  if (d0) return Uf.exports;
  d0 = 1;
  function a() {
    if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"))
      try {
        __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(a);
      } catch (u) {
        console.error(u);
      }
  }
  return a(), Uf.exports = WS(), Uf.exports;
}
/**
 * @license React
 * react-dom-client.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var m0;
function t2() {
  if (m0) return Yo;
  m0 = 1;
  var a = PS(), u = dd(), r = ey();
  function c(t) {
    var e = "https://react.dev/errors/" + t;
    if (1 < arguments.length) {
      e += "?args[]=" + encodeURIComponent(arguments[1]);
      for (var n = 2; n < arguments.length; n++)
        e += "&args[]=" + encodeURIComponent(arguments[n]);
    }
    return "Minified React error #" + t + "; visit " + e + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
  }
  function f(t) {
    return !(!t || t.nodeType !== 1 && t.nodeType !== 9 && t.nodeType !== 11);
  }
  function m(t) {
    for (var e = t, n = e; n && !n.alternate; )
      e = n, (e.flags & 4098) !== 0 && (t = e.return), n = e.return;
    for (; e.return; ) e = e.return;
    return e.tag === 3 ? t : null;
  }
  function v(t) {
    if (t.tag === 13) {
      var e = t.memoizedState;
      if (e === null && (t = t.alternate, t !== null && (e = t.memoizedState)), e !== null) return e.dehydrated;
    }
    return null;
  }
  function g(t) {
    if (t.tag === 31) {
      var e = t.memoizedState;
      if (e === null && (t = t.alternate, t !== null && (e = t.memoizedState)), e !== null) return e.dehydrated;
    }
    return null;
  }
  function p(t) {
    if (m(t) !== t)
      throw Error(c(188));
  }
  function y(t) {
    var e = t.alternate;
    if (!e) {
      if (e = m(t), e === null) throw Error(c(188));
      return e !== t ? null : t;
    }
    for (var n = t, l = e; ; ) {
      var i = n.return;
      if (i === null) break;
      var o = i.alternate;
      if (o === null) {
        if (l = i.return, l !== null) {
          n = l;
          continue;
        }
        break;
      }
      if (i.child === o.child) {
        for (o = i.child; o; ) {
          if (o === n) return p(i), t;
          if (o === l) return p(i), e;
          o = o.sibling;
        }
        throw Error(c(188));
      }
      if (n.return !== l.return) n = i, l = o;
      else {
        for (var s = !1, h = i.child; h; ) {
          if (h === n) {
            s = !0, n = i, l = o;
            break;
          }
          if (h === l) {
            s = !0, l = i, n = o;
            break;
          }
          h = h.sibling;
        }
        if (!s) {
          for (h = o.child; h; ) {
            if (h === n) {
              s = !0, n = o, l = i;
              break;
            }
            if (h === l) {
              s = !0, l = o, n = i;
              break;
            }
            h = h.sibling;
          }
          if (!s) throw Error(c(189));
        }
      }
      if (n.alternate !== l) throw Error(c(190));
    }
    if (n.tag !== 3) throw Error(c(188));
    return n.stateNode.current === n ? t : e;
  }
  function S(t) {
    var e = t.tag;
    if (e === 5 || e === 26 || e === 27 || e === 6) return t;
    for (t = t.child; t !== null; ) {
      if (e = S(t), e !== null) return e;
      t = t.sibling;
    }
    return null;
  }
  function d(t, e, n, l, i, o) {
    for (; t !== null; ) {
      if ((t.tag === 5 || t.tag === 27 || t.tag === 6) && n(t, l, i, o) || (t.tag !== 22 || t.memoizedState === null) && (e || t.tag !== 5 && t.tag !== 27) && d(
        t.child,
        e,
        n,
        l,
        i,
        o
      ))
        return !0;
      t = t.sibling;
    }
    return !1;
  }
  function x(t) {
    for (t = t.return; t !== null; ) {
      if (t.tag === 3 || t.tag === 5 || t.tag === 27) return t;
      t = t.return;
    }
    return null;
  }
  function C(t) {
    var e = !1;
    for (t = t.return; t !== null && (t.tag === 4 && (e = !0), !(t.tag === 3 || t.tag === 5 || t.tag === 27)); )
      t = t.return;
    return e;
  }
  function R(t) {
    var e = [null, null], n = x(t);
    return n === null || O(
      e,
      t,
      n.child,
      { foundSelf: !1 }
    ), e;
  }
  function O(t, e, n, l) {
    for (; n !== null; ) {
      if (n === e) l.foundSelf = !0;
      else if (n.tag === 5 || n.tag === 27 || n.tag === 6) {
        if (l.foundSelf) return t[1] = n, !0;
        t[0] = n;
      } else if ((n.tag !== 22 || n.memoizedState === null) && O(
        t,
        e,
        n.child,
        l
      ))
        return !0;
      n = n.sibling;
    }
    return !1;
  }
  function N(t) {
    switch (t.tag) {
      case 5:
      case 27:
      case 6:
        return t.stateNode;
      case 3:
        return t.stateNode.containerInfo;
      default:
        throw Error(c(559));
    }
  }
  var H = null, L = null;
  function J(t, e, n) {
    return t === n ? !0 : t === e ? (H = t, !0) : !1;
  }
  function K(t, e, n) {
    return t === n ? (L = t, !1) : t === e ? (L !== null && (H = t), !0) : !1;
  }
  function I(t) {
    if (t === null) return null;
    do
      t = t === null ? null : t.return;
    while (t && t.tag !== 5 && t.tag !== 27 && t.tag !== 3);
    return t || null;
  }
  function Z(t, e, n) {
    for (var l = 0, i = t; i; i = n(i)) l++;
    i = 0;
    for (var o = e; o; o = n(o)) i++;
    for (; 0 < l - i; ) t = n(t), l--;
    for (; 0 < i - l; ) e = n(e), i--;
    for (; l--; ) {
      if (t === e || e !== null && t === e.alternate)
        return t;
      t = n(t), e = n(e);
    }
    return null;
  }
  var X = Object.assign, Y = Symbol.for("react.element"), dt = Symbol.for("react.transitional.element"), ht = Symbol.for("react.portal"), xt = Symbol.for("react.fragment"), st = Symbol.for("react.strict_mode"), Tt = Symbol.for("react.profiler"), gt = Symbol.for("react.consumer"), yt = Symbol.for("react.context"), B = Symbol.for("react.forward_ref"), tt = Symbol.for("react.suspense"), P = Symbol.for("react.suspense_list"), at = Symbol.for("react.memo"), F = Symbol.for("react.lazy"), Bt = Symbol.for("react.activity"), Q = Symbol.for("react.legacy_hidden"), rt = Symbol.for("react.memo_cache_sentinel"), E = Symbol.for("react.view_transition"), _ = Symbol.for("react.recoverable"), V = Symbol.iterator;
  function $(t) {
    return t === null || typeof t != "object" ? null : (t = V && t[V] || t["@@iterator"], typeof t == "function" ? t : null);
  }
  var ft = Symbol.for("react.client.reference");
  function W(t) {
    if (t == null) return null;
    if (typeof t == "function")
      return t.$$typeof === ft ? null : t.displayName || t.name || null;
    if (typeof t == "string") return t;
    switch (t) {
      case xt:
        return "Fragment";
      case Tt:
        return "Profiler";
      case st:
        return "StrictMode";
      case tt:
        return "Suspense";
      case P:
        return "SuspenseList";
      case Bt:
        return "Activity";
      case E:
        return "ViewTransition";
    }
    if (typeof t == "object")
      switch (t.$$typeof) {
        case ht:
          return "Portal";
        case yt:
          return t.displayName || "Context";
        case gt:
          return (t._context.displayName || "Context") + ".Consumer";
        case B:
          var e = t.render;
          return t = t.displayName, t || (t = e.displayName || e.name || "", t = t !== "" ? "ForwardRef(" + t + ")" : "ForwardRef"), t;
        case at:
          return e = t.displayName || null, e !== null ? e : W(t.type) || "Memo";
        case F:
          e = t._payload, t = t._init;
          try {
            return W(t(e));
          } catch {
          }
      }
    return null;
  }
  var bt = Array.isArray, lt = u.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, mt = r.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, It = {
    pending: !1,
    data: null,
    method: null,
    action: null
  }, _e = [], bn = -1;
  function ye(t) {
    return { current: t };
  }
  function Qt(t) {
    0 > bn || (t.current = _e[bn], _e[bn] = null, bn--);
  }
  function Ut(t, e) {
    bn++, _e[bn] = t.current, t.current = e;
  }
  var Pt = ye(null), In = ye(null), an = ye(null), Jt = ye(null);
  function na(t, e) {
    switch (Ut(an, e), Ut(In, t), Ut(Pt, null), e.nodeType) {
      case 9:
      case 11:
        t = (t = e.documentElement) && (t = t.namespaceURI) ? vg(t) : 0;
        break;
      default:
        if (t = e.tagName, e = e.namespaceURI)
          e = vg(e), t = hg(e, t);
        else
          switch (t) {
            case "svg":
              t = 1;
              break;
            case "math":
              t = 2;
              break;
            default:
              t = 0;
          }
    }
    Qt(Pt), Ut(Pt, t);
  }
  function Je() {
    Qt(Pt), Qt(In), Qt(an);
  }
  function Li(t) {
    var e = t.memoizedState;
    e !== null && (wi._currentValue = e.memoizedState, Ut(Jt, t)), e = Pt.current;
    var n = hg(e, t.type);
    e !== n && (Ut(In, t), Ut(Pt, n));
  }
  function Ha(t) {
    In.current === t && (Qt(Pt), Qt(In)), Jt.current === t && (Qt(Jt), wi._currentValue = It);
  }
  var El, Po;
  function Sn(t) {
    if (El === void 0)
      try {
        throw Error();
      } catch (n) {
        var e = n.stack.trim().match(/\n( *(at )?)/);
        El = e && e[1] || "", Po = -1 < n.stack.indexOf(`
    at`) ? " (<anonymous>)" : -1 < n.stack.indexOf("@") ? "@unknown:0:0" : "";
      }
    return `
` + El + t + Po;
  }
  var la = !1;
  function Nn(t, e) {
    if (!t || la) return "";
    la = !0;
    var n = Error.prepareStackTrace;
    Error.prepareStackTrace = void 0;
    try {
      var l = {
        DetermineComponentFrameRoot: function() {
          try {
            if (e) {
              var G = function() {
                throw Error();
              };
              if (Object.defineProperty(G.prototype, "props", {
                set: function() {
                  throw Error();
                }
              }), typeof Reflect == "object" && Reflect.construct) {
                try {
                  Reflect.construct(G, []);
                } catch (nt) {
                  var A = nt;
                }
                Reflect.construct(t, [], G);
              } else {
                try {
                  G.call();
                } catch (nt) {
                  A = nt;
                }
                G = !1;
                try {
                  var U = Object.getOwnPropertyDescriptor(
                    t.prototype,
                    "props"
                  );
                  Object.defineProperty(t.prototype, "props", {
                    configurable: !0,
                    set: function() {
                      throw Error();
                    }
                  }), G = !0, new t();
                } finally {
                  G && (U !== void 0 ? Object.defineProperty(t.prototype, "props", U) : delete t.prototype.props);
                }
              }
            } else {
              try {
                throw Error();
              } catch (nt) {
                A = nt;
              }
              (G = t()) && typeof G.catch == "function" && G.catch(function() {
              });
            }
          } catch (nt) {
            if (nt && A && typeof nt.stack == "string")
              return [nt.stack, A.stack];
          }
          return [null, null];
        }
      };
      l.DetermineComponentFrameRoot.displayName = "DetermineComponentFrameRoot";
      var i = Object.getOwnPropertyDescriptor(
        l.DetermineComponentFrameRoot,
        "name"
      );
      i && i.configurable && Object.defineProperty(
        l.DetermineComponentFrameRoot,
        "name",
        { value: "DetermineComponentFrameRoot" }
      );
      var o = l.DetermineComponentFrameRoot(), s = o[0], h = o[1];
      if (s && h) {
        var T = s.split(`
`), z = h.split(`
`);
        for (i = l = 0; l < T.length && !T[l].includes("DetermineComponentFrameRoot"); )
          l++;
        for (; i < z.length && !z[i].includes(
          "DetermineComponentFrameRoot"
        ); )
          i++;
        if (l === T.length || i === z.length)
          for (l = T.length - 1, i = z.length - 1; 1 <= l && 0 <= i && T[l] !== z[i]; )
            i--;
        for (; 1 <= l && 0 <= i; l--, i--)
          if (T[l] !== z[i]) {
            if (l !== 1 || i !== 1)
              do
                if (l--, i--, 0 > i || T[l] !== z[i]) {
                  var j = `
` + T[l].replace(" at new ", " at ");
                  return t.displayName && j.includes("<anonymous>") && (j = j.replace("<anonymous>", t.displayName)), j;
                }
              while (1 <= l && 0 <= i);
            break;
          }
      }
    } finally {
      la = !1, Error.prepareStackTrace = n;
    }
    return (n = t ? t.displayName || t.name : "") ? Sn(n) : "";
  }
  function Wo(t, e) {
    switch (t.tag) {
      case 26:
      case 27:
      case 5:
        return Sn(t.type);
      case 16:
        return Sn("Lazy");
      case 13:
        return t.child !== e && e !== null ? Sn("Suspense Fallback") : Sn("Suspense");
      case 19:
        return Sn("SuspenseList");
      case 0:
      case 15:
        return Nn(t.type, !1);
      case 11:
        return Nn(t.type.render, !1);
      case 1:
        return Nn(t.type, !0);
      case 31:
        return Sn("Activity");
      case 30:
        return Sn("ViewTransition");
      default:
        return "";
    }
  }
  function Pn(t) {
    try {
      var e = "", n = null;
      do
        e += Wo(t, n), n = t, t = t.return;
      while (t);
      return e;
    } catch (l) {
      return `
Error generating stack: ` + l.message + `
` + l.stack;
    }
  }
  var Yi = Object.prototype.hasOwnProperty, qi = a.unstable_scheduleCallback, ja = a.unstable_cancelCallback, tu = a.unstable_shouldYield, on = a.unstable_requestPaint, Ae = a.unstable_now, Vi = a.unstable_getCurrentPriorityLevel, En = a.unstable_ImmediatePriority, Gi = a.unstable_UserBlockingPriority, Ba = a.unstable_NormalPriority, eu = a.unstable_LowPriority, Xi = a.unstable_IdlePriority, St = a.log, le = a.unstable_setDisableYieldValue, Wt = null, Gt = null;
  function He(t) {
    if (typeof St == "function" && le(t), Gt && typeof Gt.setStrictMode == "function")
      try {
        Gt.setStrictMode(Wt, t);
      } catch {
      }
  }
  var Ht = Math.clz32 ? Math.clz32 : ki, je = Math.log, un = Math.LN2;
  function ki(t) {
    return t >>>= 0, t === 0 ? 32 : 31 - (je(t) / un | 0) | 0;
  }
  var Re = 256, xl = 262144, nu = 4194304;
  function aa(t) {
    var e = t & 42;
    if (e !== 0) return e;
    switch (t & -t) {
      case 1:
        return 1;
      case 2:
        return 2;
      case 4:
        return 4;
      case 8:
        return 8;
      case 16:
        return 16;
      case 32:
        return 32;
      case 64:
        return 64;
      case 128:
        return 128;
      case 256:
      case 512:
      case 1024:
      case 2048:
      case 4096:
      case 8192:
      case 16384:
      case 32768:
      case 65536:
      case 131072:
        return t & -t;
      case 262144:
      case 524288:
      case 1048576:
      case 2097152:
        return t & 3932160;
      case 4194304:
      case 8388608:
      case 16777216:
      case 33554432:
        return t & 62914560;
      case 67108864:
        return 67108864;
      case 134217728:
        return 134217728;
      case 268435456:
        return 268435456;
      case 536870912:
        return 536870912;
      case 1073741824:
        return 0;
      default:
        return t;
    }
  }
  function lu(t, e, n) {
    var l = t.pendingLanes;
    if (l === 0) return 0;
    var i = 0, o = t.suspendedLanes, s = t.pingedLanes;
    t = t.warmLanes;
    var h = l & 134217727;
    return h !== 0 ? (l = h & ~o, l !== 0 ? i = aa(l) : (s &= h, s !== 0 ? i = aa(s) : n || (n = h & ~t, n !== 0 && (i = aa(n))))) : (h = l & ~o, h !== 0 ? i = aa(h) : s !== 0 ? i = aa(s) : n || (n = l & ~t, n !== 0 && (i = aa(n)))), i === 0 ? 0 : e !== 0 && e !== i && (e & o) === 0 && (o = i & -i, n = e & -e, o >= n || o === 32 && (n & 4194048) !== 0) ? e : i;
  }
  function Qi(t, e) {
    return (t.pendingLanes & ~(t.suspendedLanes & ~t.pingedLanes) & e) === 0;
  }
  function qd(t, e) {
    (e & 8) !== 0 && (e |= e & 32);
    var n = t.entangledLanes;
    if (n !== 0)
      for (t = t.entanglements, n &= e; 0 < n; ) {
        var l = 31 - Ht(n), i = 1 << l;
        e |= t[l], n &= ~i;
      }
    return e;
  }
  function ub(t, e) {
    switch (t) {
      case 1:
      case 2:
      case 4:
      case 8:
      case 64:
        return e + 250;
      case 16:
      case 32:
      case 128:
      case 256:
      case 512:
      case 1024:
      case 2048:
      case 4096:
      case 8192:
      case 16384:
      case 32768:
      case 65536:
      case 131072:
      case 262144:
      case 524288:
      case 1048576:
      case 2097152:
        return e + 5e3;
      case 4194304:
      case 8388608:
      case 16777216:
      case 33554432:
        return -1;
      case 67108864:
      case 134217728:
      case 268435456:
      case 536870912:
      case 1073741824:
        return -1;
      default:
        return -1;
    }
  }
  function Vd() {
    var t = nu;
    return nu <<= 1, (nu & 62914560) === 0 && (nu = 4194304), t;
  }
  function ec(t) {
    for (var e = [], n = 0; 31 > n; n++) e.push(t);
    return e;
  }
  function Zi(t, e) {
    t.pendingLanes |= e, e !== 268435456 && (t.suspendedLanes = 0, t.pingedLanes = 0, t.warmLanes = 0);
  }
  function rb(t, e, n, l, i, o) {
    var s = t.pendingLanes;
    t.pendingLanes = n, t.suspendedLanes = 0, t.pingedLanes = 0, t.warmLanes = 0, t.expiredLanes &= n, t.entangledLanes &= n, t.errorRecoveryDisabledLanes &= n, t.shellSuspendCounter = 0;
    var h = t.entanglements, T = t.expirationTimes, z = t.hiddenUpdates;
    for (n = s & ~n; 0 < n; ) {
      var j = 31 - Ht(n), G = 1 << j;
      h[j] = 0, T[j] = -1;
      var A = z[j];
      if (A !== null)
        for (z[j] = null, j = 0; j < A.length; j++) {
          var U = A[j];
          U !== null && (U.lane &= -536870913);
        }
      n &= ~G;
    }
    l !== 0 && Gd(t, l, 0), o !== 0 && i === 0 && t.tag !== 0 && (t.suspendedLanes |= o & ~(s & ~e));
  }
  function Gd(t, e, n) {
    t.pendingLanes |= e, t.suspendedLanes &= ~e;
    var l = 31 - Ht(e);
    t.entangledLanes |= e, t.entanglements[l] = t.entanglements[l] | 1073741824 | n & 261930;
  }
  function Xd(t, e) {
    var n = t.entangledLanes |= e;
    for (t = t.entanglements; n; ) {
      var l = 31 - Ht(n), i = 1 << l;
      i & e | t[l] & e && (t[l] |= e), n &= ~i;
    }
  }
  function kd(t, e) {
    var n = e & -e;
    return n = (n & 42) !== 0 ? 1 : nc(n), (n & (t.suspendedLanes | e)) !== 0 ? 0 : n;
  }
  function nc(t) {
    switch (t) {
      case 2:
        t = 1;
        break;
      case 8:
        t = 4;
        break;
      case 32:
        t = 16;
        break;
      case 256:
      case 512:
      case 1024:
      case 2048:
      case 4096:
      case 8192:
      case 16384:
      case 32768:
      case 65536:
      case 131072:
      case 262144:
      case 524288:
      case 1048576:
      case 2097152:
      case 4194304:
      case 8388608:
      case 16777216:
      case 33554432:
        t = 128;
        break;
      case 268435456:
        t = 134217728;
        break;
      default:
        t = 0;
    }
    return t;
  }
  function lc(t) {
    return t &= -t, 2 < t ? 8 < t ? (t & 134217727) !== 0 ? 32 : 268435456 : 8 : 2;
  }
  function Qd() {
    var t = mt.p;
    return t !== 0 ? t : (t = window.event, t === void 0 ? 32 : Pg(t.type));
  }
  function Zd(t, e) {
    var n = mt.p;
    try {
      return mt.p = t, e();
    } finally {
      mt.p = n;
    }
  }
  var Wn = Math.random().toString(36).slice(2), pe = "__reactFiber$" + Wn, Be = "__reactProps$" + Wn, La = "__reactContainer$" + Wn, Kd = "__reactEvents$" + Wn, cb = "__reactListeners$" + Wn, sb = "__reactHandles$" + Wn, Jd = "__reactResources$" + Wn, Ki = "__reactMarker$" + Wn, au = "__reactLoad$" + Wn;
  function iu(t) {
    delete t[pe], delete t[Be], delete t[cb], delete t[sb];
  }
  function ia(t) {
    var e;
    if (e = t[pe]) return e;
    for (var n = t.parentNode; n; ) {
      if (e = n[La] || n[pe]) {
        if (n = e.alternate, e.child !== null || n !== null && n.child !== null)
          for (t = zg(t); t !== null; ) {
            if (n = t[pe]) return n;
            t = zg(t);
          }
        return e;
      }
      t = n, n = t.parentNode;
    }
    return null;
  }
  function Ya(t) {
    if (t = t[pe] || t[La]) {
      var e = t.tag;
      if (e === 5 || e === 6 || e === 13 || e === 31 || e === 26 || e === 27 || e === 3)
        return t;
    }
    return null;
  }
  function Ji(t) {
    var e = t.tag;
    if (e === 5 || e === 26 || e === 27 || e === 6) return t.stateNode;
    throw Error(c(33));
  }
  function qa(t) {
    var e = t[Jd];
    return e || (e = t[Jd] = { hoistableStyles: /* @__PURE__ */ new Map(), hoistableScripts: /* @__PURE__ */ new Map() }), e;
  }
  function fe(t) {
    t[Ki] = !0;
  }
  function Fd(t) {
    t[au] = void 0;
  }
  var $d = /* @__PURE__ */ new Set(), Id = {};
  function oa(t, e) {
    Va(t, e), Va(t + "Capture", e);
  }
  function Va(t, e) {
    for (Id[t] = e, t = 0; t < e.length; t++)
      $d.add(e[t]);
  }
  var fb = RegExp(
    "^[:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD][:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD\\-.0-9\\u00B7\\u0300-\\u036F\\u203F-\\u2040]*$"
  ), Pd = {}, Wd = {};
  function db(t) {
    return Yi.call(Wd, t) ? !0 : Yi.call(Pd, t) ? !1 : fb.test(t) ? Wd[t] = !0 : (Pd[t] = !0, !1);
  }
  var Mt = !1;
  function tm() {
    var t = Mt;
    return Mt = !1, t;
  }
  function ou(t, e, n) {
    if (db(e))
      if (n === null) t.removeAttribute(e);
      else {
        switch (typeof n) {
          case "undefined":
          case "function":
          case "symbol":
            t.removeAttribute(e);
            return;
          case "boolean":
            var l = e.toLowerCase().slice(0, 5);
            if (l !== "data-" && l !== "aria-") {
              t.removeAttribute(e);
              return;
            }
        }
        t.setAttribute(e, n);
      }
  }
  function uu(t, e, n) {
    if (n === null) t.removeAttribute(e);
    else {
      switch (typeof n) {
        case "undefined":
        case "function":
        case "symbol":
        case "boolean":
          t.removeAttribute(e);
          return;
      }
      t.setAttribute(e, n);
    }
  }
  function tl(t, e, n, l) {
    if (l === null) t.removeAttribute(n);
    else {
      switch (typeof l) {
        case "undefined":
        case "function":
        case "symbol":
        case "boolean":
          t.removeAttribute(n);
          return;
      }
      t.setAttributeNS(e, n, l);
    }
  }
  function Fe(t) {
    switch (typeof t) {
      case "bigint":
      case "boolean":
      case "number":
      case "string":
      case "undefined":
        return t;
      case "object":
        return t;
      default:
        return "";
    }
  }
  function em(t) {
    var e = t.type;
    return (t = t.nodeName) && t.toLowerCase() === "input" && (e === "checkbox" || e === "radio");
  }
  function mb(t, e, n) {
    var l = Object.getOwnPropertyDescriptor(
      t.constructor.prototype,
      e
    );
    if (!t.hasOwnProperty(e) && typeof l < "u" && typeof l.get == "function" && typeof l.set == "function") {
      var i = l.get, o = l.set;
      return Object.defineProperty(t, e, {
        configurable: !0,
        get: function() {
          return i.call(this);
        },
        set: function(s) {
          n = "" + s, o.call(this, s);
        }
      }), Object.defineProperty(t, e, {
        enumerable: l.enumerable
      }), {
        getValue: function() {
          return n;
        },
        setValue: function(s) {
          n = "" + s;
        },
        stopTracking: function() {
          t._valueTracker = null, delete t[e];
        }
      };
    }
  }
  function ac(t) {
    if (!t._valueTracker) {
      var e = em(t) ? "checked" : "value";
      t._valueTracker = mb(
        t,
        e,
        "" + t[e]
      );
    }
  }
  function nm(t) {
    if (!t) return !1;
    var e = t._valueTracker;
    if (!e) return !0;
    var n = e.getValue(), l = "";
    return t && (l = em(t) ? t.checked ? "true" : "false" : t.value), t = l, t !== n ? (e.setValue(t), !0) : !1;
  }
  var vb = /[\n"\\]/g;
  function rn(t) {
    return t.replace(
      vb,
      function(e) {
        return "\\" + e.charCodeAt(0).toString(16) + " ";
      }
    );
  }
  function ic(t, e, n, l, i, o, s, h) {
    t.name = "", s != null && typeof s != "function" && typeof s != "symbol" && typeof s != "boolean" ? t.type = s : t.removeAttribute("type"), e != null ? s === "number" ? (e === 0 && t.value === "" || t.value != e) && (t.value = "" + Fe(e)) : t.value !== "" + Fe(e) && (t.value = "" + Fe(e)) : s !== "submit" && s !== "reset" || t.removeAttribute("value"), e != null ? s === "number" && t.value == e ? oc(t, Fe(t.value)) : oc(t, Fe(e)) : n != null ? oc(t, Fe(n)) : l != null && t.removeAttribute("value"), i == null && o != null && (t.defaultChecked = !!o), i != null && (t.checked = i && typeof i != "function" && typeof i != "symbol"), h != null && typeof h != "function" && typeof h != "symbol" && typeof h != "boolean" ? t.name = "" + Fe(h) : t.removeAttribute("name");
  }
  function lm(t, e, n, l, i, o, s, h) {
    if (o != null && typeof o != "function" && typeof o != "symbol" && typeof o != "boolean" && (t.type = o), e != null || n != null) {
      if (!(o !== "submit" && o !== "reset" || e != null)) {
        ac(t);
        return;
      }
      n = n != null ? "" + Fe(n) : "", e = e != null ? "" + Fe(e) : n, h || e === t.value || (t.value = e), t.defaultValue = e;
    }
    l = l ?? i, l = typeof l != "function" && typeof l != "symbol" && !!l, t.checked = h ? t.checked : !!l, t.defaultChecked = !!l, s != null && typeof s != "function" && typeof s != "symbol" && typeof s != "boolean" && (t.name = s), ac(t);
  }
  function oc(t, e) {
    t.defaultValue !== "" + e && (t.defaultValue = "" + e);
  }
  function Ga(t, e, n, l) {
    if (t = t.options, e) {
      e = {};
      for (var i = 0; i < n.length; i++)
        e["$" + n[i]] = !0;
      for (n = 0; n < t.length; n++)
        i = e.hasOwnProperty("$" + t[n].value), t[n].selected !== i && (t[n].selected = i), i && l && (t[n].defaultSelected = !0);
    } else {
      for (n = "" + Fe(n), e = null, i = 0; i < t.length; i++) {
        if (t[i].value === n) {
          t[i].selected = !0, l && (t[i].defaultSelected = !0);
          return;
        }
        e !== null || t[i].disabled || (e = t[i]);
      }
      e !== null && (e.selected = !0);
    }
  }
  function am(t, e, n) {
    if (e != null && (e = "" + Fe(e), e !== t.value && (t.value = e), n == null)) {
      t.defaultValue !== e && (t.defaultValue = e);
      return;
    }
    t.defaultValue = n != null ? "" + Fe(n) : "";
  }
  function im(t, e, n, l) {
    if (e == null) {
      if (l != null) {
        if (n != null) throw Error(c(92));
        if (bt(l)) {
          if (1 < l.length) throw Error(c(93));
          l = l[0];
        }
        n = l;
      }
      n == null && (n = ""), e = n;
    }
    n = Fe(e), t.defaultValue = n, l = t.textContent, l === n && l !== "" && l !== null && (t.value = l), ac(t);
  }
  function Xa(t, e) {
    if (e) {
      var n = t.firstChild;
      if (n && n === t.lastChild && n.nodeType === 3) {
        n.nodeValue = e;
        return;
      }
    }
    t.textContent = e;
  }
  var hb = new Set(
    "animationIterationCount aspectRatio borderImageOutset borderImageSlice borderImageWidth boxFlex boxFlexGroup boxOrdinalGroup columnCount columns flex flexGrow flexPositive flexShrink flexNegative flexOrder gridArea gridRow gridRowEnd gridRowSpan gridRowStart gridColumn gridColumnEnd gridColumnSpan gridColumnStart fontWeight lineClamp lineHeight opacity order orphans scale tabSize widows zIndex zoom fillOpacity floodOpacity stopOpacity strokeDasharray strokeDashoffset strokeMiterlimit strokeOpacity strokeWidth MozAnimationIterationCount MozBoxFlex MozBoxFlexGroup MozLineClamp msAnimationIterationCount msFlex msZoom msFlexGrow msFlexNegative msFlexOrder msFlexPositive msFlexShrink msGridColumn msGridColumnSpan msGridRow msGridRowSpan WebkitAnimationIterationCount WebkitBoxFlex WebKitBoxFlexGroup WebkitBoxOrdinalGroup WebkitColumnCount WebkitColumns WebkitFlex WebkitFlexGrow WebkitFlexPositive WebkitFlexShrink WebkitLineClamp".split(
      " "
    )
  );
  function om(t, e, n) {
    var l = e.indexOf("--") === 0;
    n == null || typeof n == "boolean" || n === "" ? l ? t.setProperty(e, "") : e === "float" ? t.cssFloat = "" : t[e] = "" : l ? t.setProperty(e, n) : typeof n != "number" || n === 0 || hb.has(e) ? e === "float" ? t.cssFloat = n : t[e] = ("" + n).trim() : t[e] = n + "px";
  }
  function um(t, e, n) {
    if (e != null && typeof e != "object")
      throw Error(c(62));
    if (t = t.style, n != null) {
      for (var l in n)
        !n.hasOwnProperty(l) || e != null && e.hasOwnProperty(l) || (l.indexOf("--") === 0 ? t.setProperty(l, "") : l === "float" ? t.cssFloat = "" : t[l] = "", Mt = !0);
      for (var i in e)
        l = e[i], e.hasOwnProperty(i) && n[i] !== l && (om(t, i, l), Mt = !0);
    } else
      for (var o in e)
        e.hasOwnProperty(o) && om(t, o, e[o]);
  }
  function uc(t) {
    if (t.indexOf("-") === -1) return !1;
    switch (t) {
      case "annotation-xml":
      case "color-profile":
      case "font-face":
      case "font-face-src":
      case "font-face-uri":
      case "font-face-format":
      case "font-face-name":
      case "missing-glyph":
        return !1;
      default:
        return !0;
    }
  }
  var gb = /* @__PURE__ */ new Map([
    ["acceptCharset", "accept-charset"],
    ["htmlFor", "for"],
    ["httpEquiv", "http-equiv"],
    ["crossOrigin", "crossorigin"],
    ["accentHeight", "accent-height"],
    ["alignmentBaseline", "alignment-baseline"],
    ["arabicForm", "arabic-form"],
    ["baselineShift", "baseline-shift"],
    ["capHeight", "cap-height"],
    ["clipPath", "clip-path"],
    ["clipRule", "clip-rule"],
    ["colorInterpolation", "color-interpolation"],
    ["colorInterpolationFilters", "color-interpolation-filters"],
    ["colorProfile", "color-profile"],
    ["colorRendering", "color-rendering"],
    ["dominantBaseline", "dominant-baseline"],
    ["enableBackground", "enable-background"],
    ["fillOpacity", "fill-opacity"],
    ["fillRule", "fill-rule"],
    ["floodColor", "flood-color"],
    ["floodOpacity", "flood-opacity"],
    ["fontFamily", "font-family"],
    ["fontSize", "font-size"],
    ["fontSizeAdjust", "font-size-adjust"],
    ["fontStretch", "font-stretch"],
    ["fontStyle", "font-style"],
    ["fontVariant", "font-variant"],
    ["fontWeight", "font-weight"],
    ["glyphName", "glyph-name"],
    ["glyphOrientationHorizontal", "glyph-orientation-horizontal"],
    ["glyphOrientationVertical", "glyph-orientation-vertical"],
    ["horizAdvX", "horiz-adv-x"],
    ["horizOriginX", "horiz-origin-x"],
    ["imageRendering", "image-rendering"],
    ["letterSpacing", "letter-spacing"],
    ["lightingColor", "lighting-color"],
    ["markerEnd", "marker-end"],
    ["markerMid", "marker-mid"],
    ["markerStart", "marker-start"],
    ["maskType", "mask-type"],
    ["overlinePosition", "overline-position"],
    ["overlineThickness", "overline-thickness"],
    ["paintOrder", "paint-order"],
    ["panose-1", "panose-1"],
    ["pointerEvents", "pointer-events"],
    ["renderingIntent", "rendering-intent"],
    ["shapeRendering", "shape-rendering"],
    ["stopColor", "stop-color"],
    ["stopOpacity", "stop-opacity"],
    ["strikethroughPosition", "strikethrough-position"],
    ["strikethroughThickness", "strikethrough-thickness"],
    ["strokeDasharray", "stroke-dasharray"],
    ["strokeDashoffset", "stroke-dashoffset"],
    ["strokeLinecap", "stroke-linecap"],
    ["strokeLinejoin", "stroke-linejoin"],
    ["strokeMiterlimit", "stroke-miterlimit"],
    ["strokeOpacity", "stroke-opacity"],
    ["strokeWidth", "stroke-width"],
    ["textAnchor", "text-anchor"],
    ["textDecoration", "text-decoration"],
    ["textRendering", "text-rendering"],
    ["transformOrigin", "transform-origin"],
    ["underlinePosition", "underline-position"],
    ["underlineThickness", "underline-thickness"],
    ["unicodeBidi", "unicode-bidi"],
    ["unicodeRange", "unicode-range"],
    ["unitsPerEm", "units-per-em"],
    ["vAlphabetic", "v-alphabetic"],
    ["vHanging", "v-hanging"],
    ["vIdeographic", "v-ideographic"],
    ["vMathematical", "v-mathematical"],
    ["vectorEffect", "vector-effect"],
    ["vertAdvY", "vert-adv-y"],
    ["vertOriginX", "vert-origin-x"],
    ["vertOriginY", "vert-origin-y"],
    ["wordSpacing", "word-spacing"],
    ["writingMode", "writing-mode"],
    ["xmlnsXlink", "xmlns:xlink"],
    ["xHeight", "x-height"]
  ]), yb = /^[\u0000-\u001F ]*j[\r\n\t]*a[\r\n\t]*v[\r\n\t]*a[\r\n\t]*s[\r\n\t]*c[\r\n\t]*r[\r\n\t]*i[\r\n\t]*p[\r\n\t]*t[\r\n\t]*:/i;
  function ru(t) {
    return yb.test("" + t) ? "javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')" : t;
  }
  function Dn() {
  }
  var rc = null;
  function cc(t) {
    return t = t.target || t.srcElement || window, t.correspondingUseElement && (t = t.correspondingUseElement), t.nodeType === 3 ? t.parentNode : t;
  }
  var ka = null, Qa = null;
  function rm(t) {
    var e = Ya(t);
    if (e && (t = e.stateNode)) {
      var n = t[Be] || null;
      t: switch (t = e.stateNode, e.type) {
        case "input":
          if (ic(
            t,
            n.value,
            n.defaultValue,
            n.defaultValue,
            n.checked,
            n.defaultChecked,
            n.type,
            n.name
          ), e = n.name, n.type === "radio" && e != null) {
            for (n = t; n.parentNode; ) n = n.parentNode;
            for (n = n.querySelectorAll(
              'input[name="' + rn(
                "" + e
              ) + '"][type="radio"]'
            ), e = 0; e < n.length; e++) {
              var l = n[e];
              if (l !== t && l.form === t.form) {
                var i = l[Be] || null;
                if (!i) throw Error(c(90));
                ic(
                  l,
                  i.value,
                  i.defaultValue,
                  i.defaultValue,
                  i.checked,
                  i.defaultChecked,
                  i.type,
                  i.name
                );
              }
            }
            for (e = 0; e < n.length; e++)
              l = n[e], l.form === t.form && nm(l);
          }
          break t;
        case "textarea":
          am(t, n.value, n.defaultValue);
          break t;
        case "select":
          e = n.value, e != null && Ga(t, !!n.multiple, e, !1);
      }
    }
  }
  var sc = !1;
  function cm(t, e, n) {
    if (sc) return t(e, n);
    sc = !0;
    try {
      var l = t(e);
      return l;
    } finally {
      if (sc = !1, (ka !== null || Qa !== null) && (rr(), ka && (e = ka, t = Qa, Qa = ka = null, rm(e), t)))
        for (e = 0; e < t.length; e++) rm(t[e]);
    }
  }
  function Fi(t, e) {
    var n = t.stateNode;
    if (n === null) return null;
    var l = n[Be] || null;
    if (l === null) return null;
    n = l[e];
    t: switch (e) {
      case "onClick":
      case "onClickCapture":
      case "onDoubleClick":
      case "onDoubleClickCapture":
      case "onMouseDown":
      case "onMouseDownCapture":
      case "onMouseMove":
      case "onMouseMoveCapture":
      case "onMouseUp":
      case "onMouseUpCapture":
      case "onMouseEnter":
        (l = !l.disabled) || (t = t.type, l = !(t === "button" || t === "input" || t === "select" || t === "textarea")), t = !l;
        break t;
      default:
        t = !1;
    }
    if (t) return null;
    if (n && typeof n != "function")
      throw Error(
        c(231, e, typeof n)
      );
    return n;
  }
  var el = !(typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"), fc = !1;
  if (el)
    try {
      var $i = {};
      Object.defineProperty($i, "passive", {
        get: function() {
          fc = !0;
        }
      }), window.addEventListener("test", $i, $i), window.removeEventListener("test", $i, $i);
    } catch {
      fc = !1;
    }
  var Tl = null, dc = null, cu = null;
  function sm() {
    if (cu) return cu;
    var t, e = dc, n = e.length, l, i = "value" in Tl ? Tl.value : Tl.textContent, o = i.length;
    for (t = 0; t < n && e[t] === i[t]; t++) ;
    var s = n - t;
    for (l = 1; l <= s && e[n - l] === i[o - l]; l++) ;
    return cu = i.slice(t, 1 < l ? 1 - l : void 0);
  }
  function su(t) {
    var e = t.keyCode;
    return "charCode" in t ? (t = t.charCode, t === 0 && e === 13 && (t = 13)) : t = e, t === 10 && (t = 13), 32 <= t || t === 13 ? t : 0;
  }
  function fu() {
    return !0;
  }
  function fm() {
    return !1;
  }
  function Ne(t) {
    function e(n, l, i, o, s) {
      this._reactName = n, this._targetInst = i, this.type = l, this.nativeEvent = o, this.target = s, this.currentTarget = null;
      for (var h in t)
        t.hasOwnProperty(h) && (n = t[h], this[h] = n ? n(o) : o[h]);
      return this.isDefaultPrevented = (o.defaultPrevented != null ? o.defaultPrevented : o.returnValue === !1) ? fu : fm, this.isPropagationStopped = fm, this;
    }
    return X(e.prototype, {
      preventDefault: function() {
        this.defaultPrevented = !0;
        var n = this.nativeEvent;
        n && (n.preventDefault ? n.preventDefault() : typeof n.returnValue != "unknown" && (n.returnValue = !1), this.isDefaultPrevented = fu);
      },
      stopPropagation: function() {
        var n = this.nativeEvent;
        n && (n.stopPropagation ? n.stopPropagation() : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0), this.isPropagationStopped = fu);
      },
      persist: function() {
      },
      isPersistent: fu
    }), e;
  }
  var wl = {
    eventPhase: 0,
    bubbles: 0,
    cancelable: 0,
    timeStamp: function(t) {
      return t.timeStamp || Date.now();
    },
    defaultPrevented: 0,
    isTrusted: 0
  }, du = Ne(wl), Ii = X({}, wl, { view: 0, detail: 0 }), pb = Ne(Ii), mc, vc, Pi, mu = X({}, Ii, {
    screenX: 0,
    screenY: 0,
    clientX: 0,
    clientY: 0,
    pageX: 0,
    pageY: 0,
    ctrlKey: 0,
    shiftKey: 0,
    altKey: 0,
    metaKey: 0,
    getModifierState: gc,
    button: 0,
    buttons: 0,
    relatedTarget: function(t) {
      return t.relatedTarget === void 0 ? t.fromElement === t.srcElement ? t.toElement : t.fromElement : t.relatedTarget;
    },
    movementX: function(t) {
      return "movementX" in t ? t.movementX : (t !== Pi && (Pi && t.type === "mousemove" ? (mc = t.screenX - Pi.screenX, vc = t.screenY - Pi.screenY) : vc = mc = 0, Pi = t), mc);
    },
    movementY: function(t) {
      return "movementY" in t ? t.movementY : vc;
    }
  }), dm = Ne(mu), bb = X({}, mu, { dataTransfer: 0 }), Sb = Ne(bb), Eb = X({}, Ii, { relatedTarget: 0 }), hc = Ne(Eb), xb = X({}, wl, {
    animationName: 0,
    elapsedTime: 0,
    pseudoElement: 0
  }), Tb = Ne(xb), wb = X({}, wl, {
    clipboardData: function(t) {
      return "clipboardData" in t ? t.clipboardData : window.clipboardData;
    }
  }), Cb = Ne(wb), Ob = X({}, wl, { data: 0 }), mm = Ne(Ob), _b = {
    Esc: "Escape",
    Spacebar: " ",
    Left: "ArrowLeft",
    Up: "ArrowUp",
    Right: "ArrowRight",
    Down: "ArrowDown",
    Del: "Delete",
    Win: "OS",
    Menu: "ContextMenu",
    Apps: "ContextMenu",
    Scroll: "ScrollLock",
    MozPrintableKey: "Unidentified"
  }, Ab = {
    8: "Backspace",
    9: "Tab",
    12: "Clear",
    13: "Enter",
    16: "Shift",
    17: "Control",
    18: "Alt",
    19: "Pause",
    20: "CapsLock",
    27: "Escape",
    32: " ",
    33: "PageUp",
    34: "PageDown",
    35: "End",
    36: "Home",
    37: "ArrowLeft",
    38: "ArrowUp",
    39: "ArrowRight",
    40: "ArrowDown",
    45: "Insert",
    46: "Delete",
    112: "F1",
    113: "F2",
    114: "F3",
    115: "F4",
    116: "F5",
    117: "F6",
    118: "F7",
    119: "F8",
    120: "F9",
    121: "F10",
    122: "F11",
    123: "F12",
    144: "NumLock",
    145: "ScrollLock",
    224: "Meta"
  }, Rb = {
    Alt: "altKey",
    Control: "ctrlKey",
    Meta: "metaKey",
    Shift: "shiftKey"
  };
  function Nb(t) {
    var e = this.nativeEvent;
    return e.getModifierState ? e.getModifierState(t) : (t = Rb[t]) ? !!e[t] : !1;
  }
  function gc() {
    return Nb;
  }
  var Db = X({}, Ii, {
    key: function(t) {
      if (t.key) {
        var e = _b[t.key] || t.key;
        if (e !== "Unidentified") return e;
      }
      return t.type === "keypress" ? (t = su(t), t === 13 ? "Enter" : String.fromCharCode(t)) : t.type === "keydown" || t.type === "keyup" ? Ab[t.keyCode] || "Unidentified" : "";
    },
    code: 0,
    location: 0,
    ctrlKey: 0,
    shiftKey: 0,
    altKey: 0,
    metaKey: 0,
    repeat: 0,
    locale: 0,
    getModifierState: gc,
    charCode: function(t) {
      return t.type === "keypress" ? su(t) : 0;
    },
    keyCode: function(t) {
      return t.type === "keydown" || t.type === "keyup" ? t.keyCode : 0;
    },
    which: function(t) {
      return t.type === "keypress" ? su(t) : t.type === "keydown" || t.type === "keyup" ? t.keyCode : 0;
    }
  }), zb = Ne(Db), Mb = X({}, mu, {
    pointerId: 0,
    width: 0,
    height: 0,
    pressure: 0,
    tangentialPressure: 0,
    tiltX: 0,
    tiltY: 0,
    twist: 0,
    pointerType: 0,
    isPrimary: 0
  }), vm = Ne(Mb), Ub = X({}, wl, { submitter: 0 }), Hb = Ne(Ub), jb = X({}, Ii, {
    touches: 0,
    targetTouches: 0,
    changedTouches: 0,
    altKey: 0,
    metaKey: 0,
    ctrlKey: 0,
    shiftKey: 0,
    getModifierState: gc
  }), Bb = Ne(jb), Lb = X({}, wl, {
    propertyName: 0,
    elapsedTime: 0,
    pseudoElement: 0
  }), Yb = Ne(Lb), qb = X({}, mu, {
    deltaX: function(t) {
      return "deltaX" in t ? t.deltaX : "wheelDeltaX" in t ? -t.wheelDeltaX : 0;
    },
    deltaY: function(t) {
      return "deltaY" in t ? t.deltaY : "wheelDeltaY" in t ? -t.wheelDeltaY : "wheelDelta" in t ? -t.wheelDelta : 0;
    },
    deltaZ: 0,
    deltaMode: 0
  }), Vb = Ne(qb), Gb = X({}, wl, {
    newState: 0,
    oldState: 0,
    source: 0
  }), Xb = Ne(Gb), kb = [9, 13, 27, 32], yc = el && "CompositionEvent" in window, Wi = null;
  el && "documentMode" in document && (Wi = document.documentMode);
  var Qb = el && "TextEvent" in window && !Wi, hm = el && (!yc || Wi && 8 < Wi && 11 >= Wi), gm = " ", ym = !1;
  function pm(t, e) {
    switch (t) {
      case "keyup":
        return kb.indexOf(e.keyCode) !== -1;
      case "keydown":
        return e.keyCode !== 229;
      case "keypress":
      case "mousedown":
      case "focusout":
        return !0;
      default:
        return !1;
    }
  }
  function bm(t) {
    return t = t.detail, typeof t == "object" && "data" in t ? t.data : null;
  }
  var Za = !1;
  function Zb(t, e) {
    switch (t) {
      case "compositionend":
        return bm(e);
      case "keypress":
        return e.which !== 32 ? null : (ym = !0, gm);
      case "textInput":
        return t = e.data, t === gm && ym ? null : t;
      default:
        return null;
    }
  }
  function Kb(t, e) {
    if (Za)
      return t === "compositionend" || !yc && pm(t, e) ? (t = sm(), cu = dc = Tl = null, Za = !1, t) : null;
    switch (t) {
      case "paste":
        return null;
      case "keypress":
        if (!(e.ctrlKey || e.altKey || e.metaKey) || e.ctrlKey && e.altKey) {
          if (e.char && 1 < e.char.length)
            return e.char;
          if (e.which) return String.fromCharCode(e.which);
        }
        return null;
      case "compositionend":
        return hm && e.locale !== "ko" ? null : e.data;
      default:
        return null;
    }
  }
  var Jb = {
    color: !0,
    date: !0,
    datetime: !0,
    "datetime-local": !0,
    email: !0,
    month: !0,
    number: !0,
    password: !0,
    range: !0,
    search: !0,
    tel: !0,
    text: !0,
    time: !0,
    url: !0,
    week: !0
  };
  function Sm(t) {
    var e = t && t.nodeName && t.nodeName.toLowerCase();
    return e === "input" ? !!Jb[t.type] : e === "textarea";
  }
  function Em(t, e, n, l) {
    ka ? Qa ? Qa.push(l) : Qa = [l] : ka = l, e = vr(e, "onChange"), 0 < e.length && (n = new du(
      "onChange",
      "change",
      null,
      n,
      l
    ), t.push({ event: n, listeners: e }));
  }
  var to = null, eo = null;
  function Fb(t) {
    rg(t, 0);
  }
  function vu(t) {
    var e = Ji(t);
    if (nm(e)) return t;
  }
  function xm(t, e) {
    if (t === "change") return e;
  }
  var Tm = !1;
  if (el) {
    var pc;
    if (el) {
      var bc = "oninput" in document;
      if (!bc) {
        var wm = document.createElement("div");
        wm.setAttribute("oninput", "return;"), bc = typeof wm.oninput == "function";
      }
      pc = bc;
    } else pc = !1;
    Tm = pc && (!document.documentMode || 9 < document.documentMode);
  }
  function Cm() {
    to && (to.detachEvent("onpropertychange", Om), eo = to = null);
  }
  function Om(t) {
    if (t.propertyName === "value" && vu(eo)) {
      var e = [];
      Em(
        e,
        eo,
        t,
        cc(t)
      ), cm(Fb, e);
    }
  }
  function $b(t, e, n) {
    t === "focusin" ? (Cm(), to = e, eo = n, to.attachEvent("onpropertychange", Om)) : t === "focusout" && Cm();
  }
  function Ib(t) {
    if (t === "selectionchange" || t === "keyup" || t === "keydown")
      return vu(eo);
  }
  function Pb(t, e) {
    if (t === "click") return vu(e);
  }
  function Wb(t, e) {
    if (t === "input" || t === "change")
      return vu(e);
  }
  function t1(t, e) {
    return t === e && (t !== 0 || 1 / t === 1 / e) || t !== t && e !== e;
  }
  var $e = typeof Object.is == "function" ? Object.is : t1;
  function no(t, e) {
    if ($e(t, e)) return !0;
    if (typeof t != "object" || t === null || typeof e != "object" || e === null)
      return !1;
    var n = Object.keys(t), l = Object.keys(e);
    if (n.length !== l.length) return !1;
    for (l = 0; l < n.length; l++) {
      var i = n[l];
      if (!Yi.call(e, i) || !$e(t[i], e[i]))
        return !1;
    }
    return !0;
  }
  function Sc(t) {
    if (t = t || (typeof document < "u" ? document : void 0), typeof t > "u") return null;
    try {
      return t.activeElement || t.body;
    } catch {
      return t.body;
    }
  }
  function _m(t) {
    for (; t && t.firstChild; ) t = t.firstChild;
    return t;
  }
  function Am(t, e) {
    var n = _m(t);
    t = 0;
    for (var l; n; ) {
      if (n.nodeType === 3) {
        if (l = t + n.textContent.length, t <= e && l >= e)
          return { node: n, offset: e - t };
        t = l;
      }
      t: {
        for (; n; ) {
          if (n.nextSibling) {
            n = n.nextSibling;
            break t;
          }
          n = n.parentNode;
        }
        n = void 0;
      }
      n = _m(n);
    }
  }
  function Rm(t, e) {
    return t && e ? t === e ? !0 : t && t.nodeType === 3 ? !1 : e && e.nodeType === 3 ? Rm(t, e.parentNode) : "contains" in t ? t.contains(e) : t.compareDocumentPosition ? !!(t.compareDocumentPosition(e) & 16) : !1 : !1;
  }
  function Nm(t) {
    t = t != null && t.ownerDocument != null && t.ownerDocument.defaultView != null ? t.ownerDocument.defaultView : window;
    for (var e = Sc(t.document); e instanceof t.HTMLIFrameElement; ) {
      try {
        var n = typeof e.contentWindow.location.href == "string";
      } catch {
        n = !1;
      }
      if (n) t = e.contentWindow;
      else break;
      e = Sc(t.document);
    }
    return e;
  }
  function Ec(t) {
    var e = t && t.nodeName && t.nodeName.toLowerCase();
    return e && (e === "input" && (t.type === "text" || t.type === "search" || t.type === "tel" || t.type === "url" || t.type === "password") || e === "textarea" || t.contentEditable === "true");
  }
  var e1 = el && "documentMode" in document && 11 >= document.documentMode, Ka = null, xc = null, lo = null, Tc = !1;
  function Dm(t, e, n) {
    var l = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
    Tc || Ka == null || Ka !== Sc(l) || (l = Ka, "selectionStart" in l && Ec(l) ? l = { start: l.selectionStart, end: l.selectionEnd } : (l = (l.ownerDocument && l.ownerDocument.defaultView || window).getSelection(), l = {
      anchorNode: l.anchorNode,
      anchorOffset: l.anchorOffset,
      focusNode: l.focusNode,
      focusOffset: l.focusOffset
    }), lo && no(lo, l) || (lo = l, l = vr(xc, "onSelect"), 0 < l.length && (e = new du(
      "onSelect",
      "select",
      null,
      e,
      n
    ), t.push({ event: e, listeners: l }), e.target = Ka)));
  }
  function ua(t, e) {
    var n = {};
    return n[t.toLowerCase()] = e.toLowerCase(), n["Webkit" + t] = "webkit" + e, n["Moz" + t] = "moz" + e, n;
  }
  var Ja = {
    animationend: ua("Animation", "AnimationEnd"),
    animationiteration: ua("Animation", "AnimationIteration"),
    animationstart: ua("Animation", "AnimationStart"),
    transitionrun: ua("Transition", "TransitionRun"),
    transitionstart: ua("Transition", "TransitionStart"),
    transitioncancel: ua("Transition", "TransitionCancel"),
    transitionend: ua("Transition", "TransitionEnd")
  }, wc = {}, zm = {};
  el && (zm = document.createElement("div").style, "AnimationEvent" in window || (delete Ja.animationend.animation, delete Ja.animationiteration.animation, delete Ja.animationstart.animation), "TransitionEvent" in window || delete Ja.transitionend.transition);
  function ra(t) {
    if (wc[t]) return wc[t];
    if (!Ja[t]) return t;
    var e = Ja[t], n;
    for (n in e)
      if (e.hasOwnProperty(n) && n in zm)
        return wc[t] = e[n];
    return t;
  }
  var Mm = ra("animationend"), Um = ra("animationiteration"), Hm = ra("animationstart"), n1 = ra("transitionrun"), l1 = ra("transitionstart"), a1 = ra("transitioncancel"), jm = ra("transitionend"), Bm = /* @__PURE__ */ new Map(), Cc = "abort auxClick beforeToggle cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error fullscreenChange fullscreenError gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
    " "
  );
  Cc.push("scrollEnd");
  function xn(t, e) {
    Bm.set(t, e), oa(e, [t]);
  }
  var i1 = 0;
  function nl(t, e) {
    if (t.name != null && t.name !== "auto") return t.name;
    if (e.autoName !== null) return e.autoName;
    t = On.identifierPrefix;
    var n = i1++;
    return t = "_" + t + "t_" + n.toString(32) + "_", e.autoName = t;
  }
  function Lm(t) {
    if (t == null || typeof t == "string")
      return t;
    var e = null, n = vi;
    if (n !== null)
      for (var l = 0; l < n.length; l++) {
        var i = t[n[l]];
        if (i != null) {
          if (i === "none") return "none";
          e = e == null ? i : e + (" " + i);
        }
      }
    return e ?? t.default;
  }
  function ll(t, e) {
    return t = Lm(t), e = Lm(e), e == null ? t === "auto" ? null : t : e === "auto" ? null : e;
  }
  var hu = typeof reportError == "function" ? reportError : function(t) {
    if (typeof window == "object" && typeof window.ErrorEvent == "function") {
      var e = new window.ErrorEvent("error", {
        bubbles: !0,
        cancelable: !0,
        message: typeof t == "object" && t !== null && typeof t.message == "string" ? String(t.message) : String(t),
        error: t
      });
      if (!window.dispatchEvent(e)) return;
    } else if (typeof process == "object" && typeof process.emit == "function") {
      process.emit("uncaughtException", t);
      return;
    }
    console.error(t);
  }, cn = [], Fa = 0, Oc = 0;
  function gu() {
    for (var t = Fa, e = Oc = Fa = 0; e < t; ) {
      var n = cn[e];
      cn[e++] = null;
      var l = cn[e];
      cn[e++] = null;
      var i = cn[e];
      cn[e++] = null;
      var o = cn[e];
      if (cn[e++] = null, l !== null && i !== null) {
        var s = l.pending;
        s === null ? i.next = i : (i.next = s.next, s.next = i), l.pending = i;
      }
      o !== 0 && Ym(n, i, o);
    }
  }
  function yu(t, e, n, l) {
    cn[Fa++] = t, cn[Fa++] = e, cn[Fa++] = n, cn[Fa++] = l, Oc |= l, t.lanes |= l, t = t.alternate, t !== null && (t.lanes |= l);
  }
  function _c(t, e, n, l) {
    return yu(t, e, n, l), pu(t);
  }
  function ca(t, e) {
    return yu(t, null, null, e), pu(t);
  }
  function Ym(t, e, n) {
    t.lanes |= n;
    var l = t.alternate;
    l !== null && (l.lanes |= n);
    for (var i = !1, o = t.return; o !== null; )
      o.childLanes |= n, l = o.alternate, l !== null && (l.childLanes |= n), o.tag === 22 && (t = o.stateNode, t === null || t._visibility & 1 || (i = !0)), t = o, o = o.return;
    return t.tag === 3 ? (o = t.stateNode, i && e !== null && (i = 31 - Ht(n), t = o.hiddenUpdates, l = t[i], l === null ? t[i] = [e] : l.push(e), e.lane = n | 536870912), o) : null;
  }
  function pu(t) {
    if (50 < Oo)
      throw Oo = 0, ur = null, Error(c(185));
    for (var e = t.return; e !== null; )
      t = e, e = t.return;
    return t.tag === 3 ? t.stateNode : null;
  }
  var $a = {};
  function o1(t, e, n, l) {
    this.tag = t, this.key = n, this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null, this.index = 0, this.refCleanup = this.ref = null, this.pendingProps = e, this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null, this.mode = l, this.subtreeFlags = this.flags = 0, this.deletions = null, this.childLanes = this.lanes = 0, this.alternate = null;
  }
  function Le(t, e, n, l) {
    return new o1(t, e, n, l);
  }
  function Ac(t) {
    return t = t.prototype, !(!t || !t.isReactComponent);
  }
  function al(t, e) {
    var n = t.alternate;
    return n === null ? (n = Le(
      t.tag,
      e,
      t.key,
      t.mode
    ), n.elementType = t.elementType, n.type = t.type, n.stateNode = t.stateNode, n.alternate = t, t.alternate = n) : (n.pendingProps = e, n.type = t.type, n.flags = 0, n.subtreeFlags = 0, n.deletions = null), n.flags = t.flags & 1206910976, n.childLanes = t.childLanes, n.lanes = t.lanes, n.child = t.child, n.memoizedProps = t.memoizedProps, n.memoizedState = t.memoizedState, n.updateQueue = t.updateQueue, e = t.dependencies, n.dependencies = e === null ? null : { lanes: e.lanes, firstContext: e.firstContext }, n.sibling = t.sibling, n.index = t.index, n.ref = t.ref, n.refCleanup = t.refCleanup, n;
  }
  function qm(t, e) {
    t.flags &= 1206910978;
    var n = t.alternate;
    return n === null ? (t.childLanes = 0, t.lanes = e, t.child = null, t.subtreeFlags = 0, t.memoizedProps = null, t.memoizedState = null, t.updateQueue = null, t.dependencies = null, t.stateNode = null) : (t.childLanes = n.childLanes, t.lanes = n.lanes, t.child = n.child, t.subtreeFlags = 0, t.deletions = null, t.memoizedProps = n.memoizedProps, t.memoizedState = n.memoizedState, t.updateQueue = n.updateQueue, t.type = n.type, e = n.dependencies, t.dependencies = e === null ? null : {
      lanes: e.lanes,
      firstContext: e.firstContext
    }), t;
  }
  function bu(t, e, n, l, i, o) {
    var s = 0;
    if (l = t, typeof l == "function") Ac(l) && (s = 1);
    else if (typeof l == "string")
      s = US(
        t,
        n,
        Pt.current
      ) ? 26 : t === "html" || t === "head" || t === "body" ? 27 : 5;
    else
      t: switch (l) {
        case Bt:
          return t = Le(31, n, e, i), t.elementType = Bt, t.lanes = o, t;
        case xt:
          return sa(n.children, i, o, e);
        case st:
          s = 8, i |= 24;
          break;
        case Tt:
          return t = Le(12, n, e, i | 2), t.elementType = Tt, t.lanes = o, t;
        case tt:
          return t = Le(13, n, e, i), t.elementType = tt, t.lanes = o, t;
        case P:
          return t = Le(19, n, e, i), t.elementType = P, t.lanes = o, t;
        case Q:
        case E:
          return t = i | 32, t = Le(30, n, e, t), t.elementType = E, t.lanes = o, t.stateNode = {
            autoName: null,
            paired: null,
            clones: null,
            ref: null
          }, t;
        default:
          if (typeof l == "object" && l !== null)
            switch (l.$$typeof) {
              case yt:
                s = 10;
                break t;
              case gt:
                s = 9;
                break t;
              case B:
                s = 11;
                break t;
              case at:
                s = 14;
                break t;
              case F:
                s = 16, l = null;
                break t;
            }
          s = 29, n = Error(
            c(130, t === null ? "null" : typeof t, "")
          ), l = null;
      }
    return e = Le(s, n, e, i), e.elementType = t, e.type = l, e.lanes = o, e;
  }
  function sa(t, e, n, l) {
    return t = Le(7, t, l, e), t.lanes = n, t;
  }
  function Rc(t, e, n) {
    return t = Le(6, t, null, e), t.lanes = n, t;
  }
  function Vm(t) {
    var e = Le(18, null, null, 0);
    return e.stateNode = t, e;
  }
  function Nc(t, e, n) {
    return e = Le(
      4,
      t.children !== null ? t.children : [],
      t.key,
      e
    ), e.lanes = n, e.stateNode = {
      containerInfo: t.containerInfo,
      pendingChildren: null,
      implementation: t.implementation
    }, e;
  }
  var Gm = /* @__PURE__ */ new WeakMap();
  function sn(t, e) {
    if (typeof t == "object" && t !== null) {
      var n = Gm.get(t);
      return n !== void 0 ? n : (e = {
        value: t,
        source: e,
        stack: Pn(e)
      }, Gm.set(t, e), e);
    }
    return {
      value: t,
      source: e,
      stack: Pn(e)
    };
  }
  var Ia = [], Pa = 0, Su = null, ao = 0, fn = [], dn = 0, Cl = null, zn = 1, Mn = "";
  function il(t, e) {
    Ia[Pa++] = ao, Ia[Pa++] = Su, Su = t, ao = e;
  }
  function Xm(t, e, n) {
    fn[dn++] = zn, fn[dn++] = Mn, fn[dn++] = Cl, Cl = t;
    var l = zn;
    t = Mn;
    var i = 32 - Ht(l) - 1;
    l &= ~(1 << i), n += 1;
    var o = 32 - Ht(e) + i;
    if (30 < o) {
      var s = i - i % 5;
      o = (l & (1 << s) - 1).toString(32), l >>= s, i -= s, zn = 1 << 32 - Ht(e) + i | n << i | l, Mn = o + t;
    } else
      zn = 1 << o | n << i | l, Mn = t;
  }
  function Eu(t) {
    t.return !== null && (il(t, 1), Xm(t, 1, 0));
  }
  function Dc(t) {
    for (; t === Su; )
      Su = Ia[--Pa], Ia[Pa] = null, ao = Ia[--Pa], Ia[Pa] = null;
    for (; t === Cl; )
      Cl = fn[--dn], fn[dn] = null, Mn = fn[--dn], fn[dn] = null, zn = fn[--dn], fn[dn] = null;
  }
  function km(t, e) {
    fn[dn++] = zn, fn[dn++] = Mn, fn[dn++] = Cl, zn = e.id, Mn = e.overflow, Cl = t;
  }
  var de = null, Zt = null, Ot = !1, Ol = null, mn = !1, zc = Error(c(519));
  function _l(t) {
    var e = Error(
      c(
        418,
        1 < arguments.length && arguments[1] !== void 0 && arguments[1] ? "text" : "HTML",
        ""
      )
    );
    throw io(sn(e, t)), zc;
  }
  function Qm(t) {
    var e = t.stateNode, n = t.type, l = t.memoizedProps;
    switch (e[pe] = t, e[Be] = l, n) {
      case "dialog":
        Rt("cancel", e), Rt("close", e);
        break;
      case "iframe":
      case "object":
      case "embed":
        Rt("load", e);
        break;
      case "video":
      case "audio":
        for (n = 0; n < Ao.length; n++)
          Rt(Ao[n], e);
        break;
      case "source":
        Rt("error", e);
        break;
      case "img":
      case "image":
      case "link":
        Rt("error", e), Rt("load", e);
        break;
      case "details":
        Rt("toggle", e);
        break;
      case "input":
        Rt("invalid", e), lm(
          e,
          l.value,
          l.defaultValue,
          l.checked,
          l.defaultChecked,
          l.type,
          l.name,
          !0
        );
        break;
      case "select":
        Rt("invalid", e);
        break;
      case "textarea":
        Rt("invalid", e), im(e, l.value, l.defaultValue, l.children);
    }
    n = l.children, typeof n != "string" && typeof n != "number" && typeof n != "bigint" || e.textContent === "" + n || l.suppressHydrationWarning === !0 || dg(e.textContent, n) ? (l.popover != null && (Rt("beforetoggle", e), Rt("toggle", e)), l.onScroll != null && Rt("scroll", e), l.onScrollEnd != null && Rt("scrollend", e), l.onClick != null && (e.onclick = Dn), e = !0) : e = !1, e || _l(t, !0);
  }
  function xu(t) {
    for (de = t.return; de; )
      switch (de.tag) {
        case 5:
        case 31:
        case 13:
          mn = !1;
          return;
        case 27:
        case 3:
          mn = !0;
          return;
        default:
          de = de.return;
      }
  }
  function Wa(t) {
    if (t !== de) return !1;
    if (!Ot) return xu(t), Ot = !0, !1;
    var e = t.tag, n;
    if ((n = e !== 3 && e !== 27) && ((n = e === 5) && (n = t.type, n = !(n !== "form" && n !== "button") || cf(t.type, t.memoizedProps)), n = !n), n && Zt && _l(t), xu(t), e === 13) {
      if (t = t.memoizedState, t = t !== null ? t.dehydrated : null, !t) throw Error(c(317));
      Zt = Dg(t);
    } else if (e === 31) {
      if (t = t.memoizedState, t = t !== null ? t.dehydrated : null, !t) throw Error(c(317));
      Zt = Dg(t);
    } else
      e === 27 ? (e = Zt, Xl(t.type) ? (t = pf, pf = null, Zt = t) : Zt = e) : Zt = de ? hn(t.stateNode.nextSibling) : null;
    return !0;
  }
  function fa() {
    Zt = de = null, Ot = !1;
  }
  function Mc() {
    var t = Ol;
    return t !== null && (Ve === null ? Ve = t : Ve.push.apply(
      Ve,
      t
    ), Ol = null), t;
  }
  function io(t) {
    Ol === null ? Ol = [t] : Ol.push(t);
  }
  var Uc = ye(null), da = null, ol = null;
  function Al(t, e, n) {
    Ut(Uc, e._currentValue), e._currentValue = n;
  }
  function ul(t) {
    t._currentValue = Uc.current, Qt(Uc);
  }
  function Tu(t, e, n) {
    for (; t !== null; ) {
      var l = t.alternate;
      if ((t.childLanes & e) !== e ? (t.childLanes |= e, l !== null && (l.childLanes |= e)) : l !== null && (l.childLanes & e) !== e && (l.childLanes |= e), t === n) break;
      t = t.return;
    }
  }
  function Hc(t, e, n, l) {
    var i = t.child;
    for (i !== null && (i.return = t); i !== null; ) {
      var o = i.dependencies;
      if (o !== null) {
        var s = i.child;
        o = o.firstContext;
        t: for (; o !== null; ) {
          var h = o;
          o = i;
          for (var T = 0; T < e.length; T++)
            if (h.context === e[T]) {
              o.lanes |= n, h = o.alternate, h !== null && (h.lanes |= n), Tu(
                o.return,
                n,
                t
              ), l || (s = null);
              break t;
            }
          o = h.next;
        }
      } else if (i.tag === 18) {
        if (s = i.return, s === null) throw Error(c(341));
        s.lanes |= n, o = s.alternate, o !== null && (o.lanes |= n), Tu(s, n, t), s = null;
      } else
        i.tag === 13 && i.memoizedState !== null && i.memoizedState.dehydrated === null ? (i.lanes |= n, s = i.alternate, s !== null && (s.lanes |= n), Tu(
          i.return,
          n,
          t
        ), s = i.child, s = s !== null ? s.sibling : null) : s = i.child;
      if (s !== null) s.return = i;
      else
        for (s = i; s !== null; ) {
          if (s === t) {
            s = null;
            break;
          }
          if (i = s.sibling, i !== null) {
            i.return = s.return, s = i;
            break;
          }
          s = s.return;
        }
      i = s;
    }
  }
  function ma(t, e, n, l) {
    t = null;
    for (var i = e, o = !1; i !== null; ) {
      if (!o) {
        if ((i.flags & 524288) !== 0) o = !0;
        else if ((i.flags & 262144) !== 0) break;
      }
      if (i.tag === 10) {
        var s = i.alternate;
        if (s === null) throw Error(c(387));
        if (s = s.memoizedProps, s !== null) {
          var h = i.type;
          $e(i.pendingProps.value, s.value) || (t !== null ? t.push(h) : t = [h]);
        }
      } else if (i === Jt.current) {
        if (s = i.alternate, s === null) throw Error(c(387));
        s.memoizedState.memoizedState !== i.memoizedState.memoizedState && (t !== null ? t.push(wi) : t = [wi]);
      }
      i = i.return;
    }
    return t !== null && Hc(
      e,
      t,
      n,
      l
    ), e.flags |= 262144, t !== null;
  }
  function wu(t) {
    for (t = t.firstContext; t !== null; ) {
      if (!$e(
        t.context._currentValue,
        t.memoizedValue
      ))
        return !0;
      t = t.next;
    }
    return !1;
  }
  function va(t) {
    da = t, ol = null, t = t.dependencies, t !== null && (t.firstContext = null);
  }
  function be(t) {
    return Zm(da, t);
  }
  function Cu(t, e) {
    return da === null && va(t), Zm(t, e);
  }
  function Zm(t, e) {
    var n = e._currentValue;
    if (e = { context: e, memoizedValue: n, next: null }, ol === null) {
      if (t === null) throw Error(c(308));
      ol = e, t.dependencies = { lanes: 0, firstContext: e }, t.flags |= 524288;
    } else ol = ol.next = e;
    return n;
  }
  var u1 = typeof AbortController < "u" ? AbortController : function() {
    var t = [], e = this.signal = {
      aborted: !1,
      addEventListener: function(n, l) {
        t.push(l);
      }
    };
    this.abort = function() {
      e.aborted = !0, t.forEach(function(n) {
        return n();
      });
    };
  }, r1 = a.unstable_scheduleCallback, c1 = a.unstable_NormalPriority, ae = {
    $$typeof: yt,
    Consumer: null,
    Provider: null,
    _currentValue: null,
    _currentValue2: null,
    _threadCount: 0
  };
  function jc() {
    return {
      controller: new u1(),
      data: /* @__PURE__ */ new Map(),
      refCount: 0
    };
  }
  function oo(t) {
    t.refCount--, t.refCount === 0 && r1(c1, function() {
      t.controller.abort();
    });
  }
  function Km(t, e) {
    if ((t.pendingLanes & 4194048) !== 0) {
      var n = t.transitionTypes;
      for (n === null && (n = t.transitionTypes = []), t = 0; t < e.length; t++) {
        var l = e[t];
        n.indexOf(l) === -1 && n.push(l);
      }
    }
  }
  var uo = null;
  function s1(t) {
    var e = t.transitionTypes;
    return t.transitionTypes = null, e;
  }
  var ro = null, Bc = 0, ha = 0, ti = null;
  function f1(t, e) {
    if (ro === null) {
      var n = ro = [];
      Bc = 0, ha = Ws(), ti = {
        status: "pending",
        value: void 0,
        then: function(l) {
          n.push(l);
        }
      };
    }
    return Bc++, e.then(Jm, Jm), e;
  }
  function Jm() {
    if (--Bc === 0 && (uo = null, ro !== null)) {
      ti !== null && (ti.status = "fulfilled");
      var t = ro;
      ro = null, ha = 0, ti = null;
      for (var e = 0; e < t.length; e++) (0, t[e])();
    }
  }
  function d1(t, e) {
    var n = [], l = {
      status: "pending",
      value: null,
      reason: null,
      then: function(i) {
        n.push(i);
      }
    };
    return t.then(
      function() {
        l.status = "fulfilled", l.value = e;
        for (var i = 0; i < n.length; i++) (0, n[i])(e);
      },
      function(i) {
        for (l.status = "rejected", l.reason = i, i = 0; i < n.length; i++)
          (0, n[i])(void 0);
      }
    ), l;
  }
  var Fm = lt.S;
  lt.S = function(t, e) {
    if (Vh = Ae(), typeof e == "object" && e !== null && typeof e.then == "function" && f1(t, e), uo !== null)
      for (var n = pi; n !== null; )
        Km(n, uo), n = n.next;
    if (n = t.types, n !== null) {
      for (var l = pi; l !== null; )
        Km(l, n), l = l.next;
      if (ha !== 0) {
        l = uo, l === null && (l = uo = []);
        for (var i = 0; i < n.length; i++) {
          var o = n[i];
          l.indexOf(o) === -1 && l.push(o);
        }
      }
    }
    Fm !== null && Fm(t, e);
  };
  var ga = ye(null);
  function Lc() {
    var t = ga.current;
    return t !== null ? t : kt.pooledCache;
  }
  function Ou(t, e) {
    e === null ? Ut(ga, ga.current) : Ut(ga, e.pool);
  }
  function $m() {
    var t = Lc();
    return t === null ? null : { parent: ae._currentValue, pool: t };
  }
  var ei = Error(c(460)), Yc = Error(c(474)), _u = Error(c(542)), Au = { then: function() {
  } };
  function Im(t) {
    return t = t.status, t === "fulfilled" || t === "rejected";
  }
  function Pm(t, e, n) {
    switch (n = t[n], n === void 0 ? t.push(e) : n !== e && (e.then(Dn, Dn), e = n), e.status) {
      case "fulfilled":
        return e.value;
      case "rejected":
        throw t = e.reason, tv(t), t === void 0 && !("reason" in e) ? Error(c(600)) : t;
      default:
        if (typeof e.status == "string") e.then(Dn, Dn);
        else {
          if (t = kt, t !== null && 100 < t.shellSuspendCounter)
            throw Error(c(482));
          t = e, t.status = "pending", t.then(
            function(l) {
              if (e.status === "pending") {
                var i = e;
                i.status = "fulfilled", i.value = l;
              }
            },
            function(l) {
              if (e.status === "pending") {
                var i = e;
                i.status = "rejected", i.reason = l;
              }
            }
          );
        }
        switch (e.status) {
          case "fulfilled":
            return e.value;
          case "rejected":
            throw t = e.reason, tv(t), t;
        }
        throw pa = e, ei;
    }
  }
  function ya(t) {
    try {
      var e = t._init;
      return e(t._payload);
    } catch (n) {
      throw n !== null && typeof n == "object" && typeof n.then == "function" ? (pa = n, ei) : n;
    }
  }
  var pa = null;
  function Wm() {
    if (pa === null) throw Error(c(459));
    var t = pa;
    return pa = null, t;
  }
  function tv(t) {
    if (t === ei || t === _u)
      throw Error(c(483));
  }
  var ni = null, co = 0;
  function Ru(t) {
    var e = co;
    return co += 1, ni === null && (ni = []), Pm(ni, t, e);
  }
  function Rl(t, e) {
    e = e.props.ref, t.ref = e !== void 0 ? e : null;
  }
  function Nu(t, e) {
    throw e.$$typeof === Y ? Error(c(525)) : (t = Object.prototype.toString.call(e), Error(
      c(
        31,
        t === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : t
      )
    ));
  }
  function ev(t) {
    function e(D, w) {
      if (t) {
        var M = D.deletions;
        M === null ? (D.deletions = [w], D.flags |= 16) : M.push(w);
      }
    }
    function n(D, w) {
      if (!t) return null;
      for (; w !== null; )
        e(D, w), w = w.sibling;
      return null;
    }
    function l(D) {
      for (var w = /* @__PURE__ */ new Map(); D !== null; )
        D.key === null ? w.set(D.index, D) : w.set(D.key, D), D = D.sibling;
      return w;
    }
    function i(D, w) {
      return D = al(D, w), D.index = 0, D.sibling = null, D;
    }
    function o(D, w, M) {
      return D.index = M, t ? (M = D.alternate, M !== null ? (M = M.index, M < w ? (D.flags |= 2, w) : M) : (D.flags |= 134217730, w)) : (D.flags |= 1048576, w);
    }
    function s(D) {
      return t && D.alternate === null && (D.flags |= 134217730), D;
    }
    function h(D, w, M, q) {
      return w === null || w.tag !== 6 ? (w = Rc(M, D.mode, q), w.return = D, w) : (w = i(w, M), w.return = D, w);
    }
    function T(D, w, M, q) {
      var it = M.type;
      return it === xt ? (D = j(
        D,
        w,
        M.props.children,
        q,
        M.key
      ), Rl(D, M), D) : w !== null && (w.elementType === it || typeof it == "object" && it !== null && it.$$typeof === F && ya(it) === w.type) ? (w = i(w, M.props), Rl(w, M), w.return = D, w) : (w = bu(
        M.type,
        M.key,
        M.props,
        null,
        D.mode,
        q
      ), Rl(w, M), w.return = D, w);
    }
    function z(D, w, M, q) {
      return w === null || w.tag !== 4 || w.stateNode.containerInfo !== M.containerInfo || w.stateNode.implementation !== M.implementation ? (w = Nc(M, D.mode, q), w.return = D, w) : (w = i(w, M.children || []), w.return = D, w);
    }
    function j(D, w, M, q, it) {
      return w === null || w.tag !== 7 ? (w = sa(
        M,
        D.mode,
        q,
        it
      ), w.return = D, w) : (w = i(w, M), w.return = D, w);
    }
    function G(D, w, M) {
      if (typeof w == "string" && w !== "" || typeof w == "number" || typeof w == "bigint")
        return w = Rc(
          "" + w,
          D.mode,
          M
        ), w.return = D, w;
      if (typeof w == "object" && w !== null) {
        switch (w.$$typeof) {
          case dt:
            return M = bu(
              w.type,
              w.key,
              w.props,
              null,
              D.mode,
              M
            ), Rl(M, w), M.return = D, M;
          case ht:
            return w = Nc(
              w,
              D.mode,
              M
            ), w.return = D, w;
          case F:
            return w = ya(w), G(D, w, M);
        }
        if (bt(w) || $(w))
          return w = sa(
            w,
            D.mode,
            M,
            null
          ), w.return = D, w;
        if (typeof w.then == "function")
          return G(D, Ru(w), M);
        if (w.$$typeof === yt)
          return G(
            D,
            Cu(D, w),
            M
          );
        Nu(D, w);
      }
      return null;
    }
    function A(D, w, M, q) {
      var it = w !== null ? w.key : null;
      if (typeof M == "string" && M !== "" || typeof M == "number" || typeof M == "bigint")
        return it !== null ? null : h(D, w, "" + M, q);
      if (typeof M == "object" && M !== null) {
        switch (M.$$typeof) {
          case dt:
            return M.key === it ? T(D, w, M, q) : null;
          case ht:
            return M.key === it ? z(D, w, M, q) : null;
          case F:
            return M = ya(M), A(D, w, M, q);
        }
        if (bt(M) || $(M))
          return it !== null ? null : j(D, w, M, q, null);
        if (typeof M.then == "function")
          return A(
            D,
            w,
            Ru(M),
            q
          );
        if (M.$$typeof === yt)
          return A(
            D,
            w,
            Cu(D, M),
            q
          );
        Nu(D, M);
      }
      return null;
    }
    function U(D, w, M, q, it) {
      if (typeof q == "string" && q !== "" || typeof q == "number" || typeof q == "bigint")
        return D = D.get(M) || null, h(w, D, "" + q, it);
      if (typeof q == "object" && q !== null) {
        switch (q.$$typeof) {
          case dt:
            return D = D.get(
              q.key === null ? M : q.key
            ) || null, T(w, D, q, it);
          case ht:
            return D = D.get(
              q.key === null ? M : q.key
            ) || null, z(w, D, q, it);
          case F:
            return q = ya(q), U(
              D,
              w,
              M,
              q,
              it
            );
        }
        if (bt(q) || $(q))
          return D = D.get(M) || null, j(w, D, q, it, null);
        if (typeof q.then == "function")
          return U(
            D,
            w,
            M,
            Ru(q),
            it
          );
        if (q.$$typeof === yt)
          return U(
            D,
            w,
            M,
            Cu(w, q),
            it
          );
        Nu(w, q);
      }
      return null;
    }
    function nt(D, w, M, q) {
      for (var it = null, Dt = null, vt = w, pt = w = 0, ue = null; vt !== null && pt < M.length; pt++) {
        vt.index > pt ? (ue = vt, vt = null) : ue = vt.sibling;
        var zt = A(
          D,
          vt,
          M[pt],
          q
        );
        if (zt === null) {
          vt === null && (vt = ue);
          break;
        }
        t && vt && zt.alternate === null && e(D, vt), w = o(zt, w, pt), Dt === null ? it = zt : Dt.sibling = zt, Dt = zt, vt = ue;
      }
      if (pt === M.length)
        return n(D, vt), Ot && il(D, pt), it;
      if (vt === null) {
        for (; pt < M.length; pt++)
          vt = G(D, M[pt], q), vt !== null && (w = o(
            vt,
            w,
            pt
          ), Dt === null ? it = vt : Dt.sibling = vt, Dt = vt);
        return Ot && il(D, pt), it;
      }
      for (vt = l(vt); pt < M.length; pt++)
        ue = U(
          vt,
          D,
          pt,
          M[pt],
          q
        ), ue !== null && (t && (zt = ue.alternate, zt !== null && vt.delete(zt.key === null ? pt : zt.key)), w = o(
          ue,
          w,
          pt
        ), Dt === null ? it = ue : Dt.sibling = ue, Dt = ue);
      return t && vt.forEach(function(Jl) {
        return e(D, Jl);
      }), Ot && il(D, pt), it;
    }
    function ct(D, w, M, q) {
      if (M == null) throw Error(c(151));
      for (var it = null, Dt = null, vt = w, pt = w = 0, ue = null, zt = M.next(); vt !== null && !zt.done; pt++, zt = M.next()) {
        vt.index > pt ? (ue = vt, vt = null) : ue = vt.sibling;
        var Jl = A(D, vt, zt.value, q);
        if (Jl === null) {
          vt === null && (vt = ue);
          break;
        }
        t && vt && Jl.alternate === null && e(D, vt), w = o(Jl, w, pt), Dt === null ? it = Jl : Dt.sibling = Jl, Dt = Jl, vt = ue;
      }
      if (zt.done)
        return n(D, vt), Ot && il(D, pt), it;
      if (vt === null) {
        for (; !zt.done; pt++, zt = M.next())
          zt = G(D, zt.value, q), zt !== null && (w = o(zt, w, pt), Dt === null ? it = zt : Dt.sibling = zt, Dt = zt);
        return Ot && il(D, pt), it;
      }
      for (vt = l(vt); !zt.done; pt++, zt = M.next())
        zt = U(vt, D, pt, zt.value, q), zt !== null && (t && (ue = zt.alternate, ue !== null && vt.delete(
          ue.key === null ? pt : ue.key
        )), w = o(zt, w, pt), Dt === null ? it = zt : Dt.sibling = zt, Dt = zt);
      return t && vt.forEach(function(ZS) {
        return e(D, ZS);
      }), Ot && il(D, pt), it;
    }
    function Ct(D, w, M, q) {
      if (typeof M == "object" && M !== null && M.type === xt && M.key === null && M.props.ref === void 0 && (M = M.props.children), typeof M == "object" && M !== null) {
        switch (M.$$typeof) {
          case dt:
            t: {
              for (var it = M.key; w !== null; ) {
                if (w.key === it) {
                  if (it = M.type, it === xt) {
                    if (w.tag === 7) {
                      n(
                        D,
                        w.sibling
                      ), q = i(
                        w,
                        M.props.children
                      ), Rl(q, M), q.return = D, D = q;
                      break t;
                    }
                  } else if (w.elementType === it || typeof it == "object" && it !== null && it.$$typeof === F && ya(it) === w.type) {
                    n(
                      D,
                      w.sibling
                    ), q = i(w, M.props), Rl(q, M), q.return = D, D = q;
                    break t;
                  }
                  n(D, w);
                  break;
                } else e(D, w);
                w = w.sibling;
              }
              M.type === xt ? (q = sa(
                M.props.children,
                D.mode,
                q,
                M.key
              ), Rl(q, M), q.return = D, D = q) : (q = bu(
                M.type,
                M.key,
                M.props,
                null,
                D.mode,
                q
              ), Rl(q, M), q.return = D, D = q);
            }
            return s(D);
          case ht:
            t: {
              for (it = M.key; w !== null; ) {
                if (w.key === it)
                  if (w.tag === 4 && w.stateNode.containerInfo === M.containerInfo && w.stateNode.implementation === M.implementation) {
                    n(
                      D,
                      w.sibling
                    ), q = i(w, M.children || []), q.return = D, D = q;
                    break t;
                  } else {
                    n(D, w);
                    break;
                  }
                else e(D, w);
                w = w.sibling;
              }
              q = Nc(M, D.mode, q), q.return = D, D = q;
            }
            return s(D);
          case F:
            return M = ya(M), Ct(
              D,
              w,
              M,
              q
            );
        }
        if (bt(M))
          return nt(
            D,
            w,
            M,
            q
          );
        if ($(M)) {
          if (it = $(M), typeof it != "function") throw Error(c(150));
          return M = it.call(M), ct(
            D,
            w,
            M,
            q
          );
        }
        if (typeof M.then == "function")
          return Ct(
            D,
            w,
            Ru(M),
            q
          );
        if (M.$$typeof === yt)
          return Ct(
            D,
            w,
            Cu(D, M),
            q
          );
        Nu(D, M);
      }
      return typeof M == "string" && M !== "" || typeof M == "number" || typeof M == "bigint" ? (M = "" + M, w !== null && w.tag === 6 ? (n(D, w.sibling), q = i(w, M), q.return = D, D = q) : (n(D, w), q = Rc(M, D.mode, q), q.return = D, D = q), s(D)) : n(D, w);
    }
    return function(D, w, M, q) {
      try {
        co = 0;
        var it = Ct(
          D,
          w,
          M,
          q
        );
        return ni = null, it;
      } catch (vt) {
        if (vt === ei || vt === _u) throw vt;
        var Dt = Le(29, vt, null, D.mode);
        return Dt.lanes = q, Dt.return = D, Dt;
      } finally {
      }
    };
  }
  var ba = ev(!0), nv = ev(!1), Nl = !1;
  function qc(t) {
    t.updateQueue = {
      baseState: t.memoizedState,
      firstBaseUpdate: null,
      lastBaseUpdate: null,
      shared: { pending: null, lanes: 0, hiddenCallbacks: null },
      callbacks: null
    };
  }
  function Vc(t, e) {
    t = t.updateQueue, e.updateQueue === t && (e.updateQueue = {
      baseState: t.baseState,
      firstBaseUpdate: t.firstBaseUpdate,
      lastBaseUpdate: t.lastBaseUpdate,
      shared: t.shared,
      callbacks: null
    });
  }
  function Dl(t) {
    return { lane: t, tag: 0, payload: null, callback: null, next: null };
  }
  function zl(t, e, n) {
    var l = t.updateQueue;
    if (l === null) return null;
    if (l = l.shared, (jt & 2) !== 0) {
      var i = l.pending;
      return i === null ? e.next = e : (e.next = i.next, i.next = e), l.pending = e, e = pu(t), Ym(t, null, n), e;
    }
    return yu(t, l, e, n), pu(t);
  }
  function so(t, e, n) {
    if (e = e.updateQueue, e !== null && (e = e.shared, (n & 4194048) !== 0)) {
      var l = e.lanes;
      l &= t.pendingLanes, n |= l, e.lanes = n, Xd(t, n);
    }
  }
  function Gc(t, e) {
    var n = t.updateQueue, l = t.alternate;
    if (l !== null && (l = l.updateQueue, n === l)) {
      var i = null, o = null;
      if (n = n.firstBaseUpdate, n !== null) {
        do {
          var s = {
            lane: n.lane,
            tag: n.tag,
            payload: n.payload,
            callback: null,
            next: null
          };
          o === null ? i = o = s : o = o.next = s, n = n.next;
        } while (n !== null);
        o === null ? i = o = e : o = o.next = e;
      } else i = o = e;
      n = {
        baseState: l.baseState,
        firstBaseUpdate: i,
        lastBaseUpdate: o,
        shared: l.shared,
        callbacks: l.callbacks
      }, t.updateQueue = n;
      return;
    }
    t = n.lastBaseUpdate, t === null ? n.firstBaseUpdate = e : t.next = e, n.lastBaseUpdate = e;
  }
  var Xc = !1;
  function fo() {
    if (Xc) {
      var t = ti;
      if (t !== null) throw t;
    }
  }
  function mo(t, e, n, l) {
    Xc = !1;
    var i = t.updateQueue;
    Nl = !1;
    var o = i.firstBaseUpdate, s = i.lastBaseUpdate, h = i.shared.pending;
    if (h !== null) {
      i.shared.pending = null;
      var T = h, z = T.next;
      T.next = null, s === null ? o = z : s.next = z, s = T;
      var j = t.alternate;
      j !== null && (j = j.updateQueue, h = j.lastBaseUpdate, h !== s && (h === null ? j.firstBaseUpdate = z : h.next = z, j.lastBaseUpdate = T));
    }
    if (o !== null) {
      var G = i.baseState;
      s = 0, j = z = T = null, h = o;
      do {
        var A = h.lane & -536870913, U = A !== h.lane;
        if (U ? (Nt & A) === A : (l & A) === A) {
          A !== 0 && A === ha && (Xc = !0), j !== null && (j = j.next = {
            lane: 0,
            tag: h.tag,
            payload: h.payload,
            callback: null,
            next: null
          });
          t: {
            var nt = t, ct = h;
            A = e;
            var Ct = n;
            switch (ct.tag) {
              case 1:
                if (nt = ct.payload, typeof nt == "function") {
                  G = nt.call(Ct, G, A);
                  break t;
                }
                G = nt;
                break t;
              case 3:
                nt.flags = nt.flags & -65537 | 128;
              case 0:
                if (nt = ct.payload, A = typeof nt == "function" ? nt.call(Ct, G, A) : nt, A == null) break t;
                G = X({}, G, A);
                break t;
              case 2:
                Nl = !0;
            }
          }
          A = h.callback, A !== null && (t.flags |= 64, U && (t.flags |= 8192), U = i.callbacks, U === null ? i.callbacks = [A] : U.push(A));
        } else
          U = {
            lane: A,
            tag: h.tag,
            payload: h.payload,
            callback: h.callback,
            next: null
          }, j === null ? (z = j = U, T = G) : j = j.next = U, s |= A;
        if (h = h.next, h === null) {
          if (h = i.shared.pending, h === null)
            break;
          U = h, h = U.next, U.next = null, i.lastBaseUpdate = U, i.shared.pending = null;
        }
      } while (!0);
      j === null && (T = G), i.baseState = T, i.firstBaseUpdate = z, i.lastBaseUpdate = j, o === null && (i.shared.lanes = 0), Yl |= s, t.lanes = s, t.memoizedState = G;
    }
  }
  function lv(t, e) {
    if (typeof t != "function")
      throw Error(c(191, t));
    t.call(e);
  }
  function av(t, e) {
    var n = t.callbacks;
    if (n !== null)
      for (t.callbacks = null, t = 0; t < n.length; t++)
        lv(n[t], e);
  }
  var Ml = ye(null), Du = ye(0);
  function iv(t, e) {
    t = dl, Ut(Du, t), Ut(Ml, e), dl = t | e.baseLanes;
  }
  function kc() {
    Ut(Du, dl), Ut(Ml, Ml.current);
  }
  function Qc() {
    dl = Du.current, Qt(Ml), Qt(Du);
  }
  var Se = ye(null), Ce = null;
  function Ul(t) {
    var e = t.alternate;
    Ut(Ee, Ee.current & 1), Ut(Se, t), Ce === null && (e === null || Ml.current !== null || e.memoizedState !== null) && (Ce = t);
  }
  function Zc(t) {
    Ut(Ee, Ee.current), Ut(Se, t), Ce === null && (Ce = t);
  }
  function ov(t) {
    t.tag === 22 ? (Ut(Ee, Ee.current), Ut(Se, t), Ce === null && (Ce = t)) : Hl();
  }
  function Hl() {
    Ut(Ee, Ee.current), Ut(Se, Se.current);
  }
  function Ie(t) {
    Qt(Se), Ce === t && (Ce = null), Qt(Ee);
  }
  var Ee = ye(0);
  function vo(t, e) {
    Ut(Se, Se.current), Ut(Ee, e);
  }
  function Kc(t) {
    Qt(Ee), Qt(Se), Ce === t && (Ce = null);
  }
  function zu(t) {
    for (var e = t; e !== null; ) {
      if (e.tag === 13) {
        var n = e.memoizedState;
        if (n !== null && (n = n.dehydrated, n === null || gf(n) || yf(n)))
          return e;
      } else if (e.tag === 19 && e.memoizedProps.revealOrder !== "independent") {
        if ((e.flags & 128) !== 0) return e;
      } else if (e.child !== null) {
        e.child.return = e, e = e.child;
        continue;
      }
      if (e === t) break;
      for (; e.sibling === null; ) {
        if (e.return === null || e.return === t) return null;
        e = e.return;
      }
      e.sibling.return = e.return, e = e.sibling;
    }
    return null;
  }
  var rl = 0, wt = null, Xt = null, ie = null, Mu = !1, li = !1, Sa = !1, Uu = 0, ho = 0, ai = null, m1 = 0;
  function te() {
    throw Error(c(321));
  }
  function Jc(t, e) {
    if (e === null) return !1;
    for (var n = 0; n < e.length && n < t.length; n++)
      if (!$e(t[n], e[n])) return !1;
    return !0;
  }
  function Fc(t, e, n, l, i, o) {
    return rl = o, wt = e, e.memoizedState = null, e.updateQueue = null, e.lanes = 0, lt.H = t === null || t.memoizedState === null ? Xv : kv, Sa = !1, o = n(l, i), Sa = !1, li && (o = rv(
      e,
      n,
      l,
      i
    )), uv(t), o;
  }
  function uv(t) {
    lt.H = Vu;
    var e = Xt !== null && Xt.next !== null;
    if (rl = 0, ie = Xt = wt = null, Mu = !1, ho = 0, ai = null, e) throw Error(c(300));
    t === null || oe || (t = t.dependencies, t !== null && wu(t) && (oe = !0));
  }
  function rv(t, e, n, l) {
    wt = t;
    var i = 0;
    do {
      if (li && (ai = null), ho = 0, li = !1, 25 <= i) throw Error(c(301));
      if (i += 1, ie = Xt = null, t.updateQueue != null) {
        var o = t.updateQueue;
        o.lastEffect = null, o.events = null, o.stores = null, o.memoCache != null && (o.memoCache.index = 0);
      }
      lt.H = E1, o = e(n, l);
    } while (li);
    return o;
  }
  function v1() {
    var t = lt.H, e = t.useState()[0];
    return e = typeof e.then == "function" ? go(e) : e, t = t.useState()[0], (Xt !== null ? Xt.memoizedState : null) !== t && (wt.flags |= 1024), e;
  }
  function $c() {
    var t = Uu !== 0;
    return Uu = 0, t;
  }
  function Ic(t, e, n) {
    e.updateQueue = t.updateQueue, e.flags &= -2053, t.lanes &= ~n;
  }
  function Pc(t) {
    if (Mu) {
      for (t = t.memoizedState; t !== null; ) {
        var e = t.queue;
        e !== null && (e.pending = null), t = t.next;
      }
      Mu = !1;
    }
    rl = 0, ie = Xt = wt = null, li = !1, ho = Uu = 0, ai = null;
  }
  function De() {
    var t = {
      memoizedState: null,
      baseState: null,
      baseQueue: null,
      queue: null,
      next: null
    };
    return ie === null ? wt.memoizedState = ie = t : ie = ie.next = t, ie;
  }
  function ne() {
    if (Xt === null) {
      var t = wt.alternate;
      t = t !== null ? t.memoizedState : null;
    } else t = Xt.next;
    var e = ie === null ? wt.memoizedState : ie.next;
    if (e !== null)
      ie = e, Xt = t;
    else {
      if (t === null)
        throw wt.alternate === null ? Error(c(467)) : Error(c(310));
      Xt = t, t = {
        memoizedState: Xt.memoizedState,
        baseState: Xt.baseState,
        baseQueue: Xt.baseQueue,
        queue: Xt.queue,
        next: null
      }, ie === null ? wt.memoizedState = ie = t : ie = ie.next = t;
    }
    return ie;
  }
  function Hu() {
    return { lastEffect: null, events: null, stores: null, memoCache: null };
  }
  function go(t) {
    var e = ho;
    return ho += 1, ai === null && (ai = []), t = Pm(ai, t, e), e = wt, (ie === null ? e.memoizedState : ie.next) === null && (e = e.alternate, lt.H = e === null || e.memoizedState === null ? Xv : kv), t;
  }
  function ju(t) {
    if (t !== null && typeof t == "object") {
      if (typeof t.then == "function") return go(t);
      if (t.$$typeof === _) return;
      if (t.$$typeof === yt) return be(t);
    }
    throw Error(c(438, String(t)));
  }
  function Wc(t) {
    var e = null, n = wt.updateQueue;
    if (n !== null && (e = n.memoCache), e == null) {
      var l = wt.alternate;
      l !== null && (l = l.updateQueue, l !== null && (l = l.memoCache, l != null && (e = {
        data: l.data.map(function(i) {
          return i.slice();
        }),
        index: 0
      })));
    }
    if (e == null && (e = { data: [], index: 0 }), n === null && (n = Hu(), wt.updateQueue = n), n.memoCache = e, n = e.data[e.index], n === void 0)
      for (n = e.data[e.index] = Array(t), l = 0; l < t; l++)
        n[l] = rt;
    return e.index++, n;
  }
  function cl(t, e) {
    return typeof e == "function" ? e(t) : e;
  }
  function Bu(t) {
    var e = ne();
    return ts(e, Xt, t);
  }
  function ts(t, e, n) {
    var l = t.queue;
    if (l === null) throw Error(c(311));
    l.lastRenderedReducer = n;
    var i = t.baseQueue, o = l.pending;
    if (o !== null) {
      if (i !== null) {
        var s = i.next;
        i.next = o.next, o.next = s;
      }
      e.baseQueue = i = o, l.pending = null;
    }
    if (o = t.baseState, i === null) t.memoizedState = o;
    else {
      e = i.next;
      var h = s = null, T = null, z = e, j = !1;
      do {
        var G = z.lane & -536870913;
        if (G !== z.lane ? (Nt & G) === G : (rl & G) === G) {
          var A = z.revertLane;
          if (A === 0)
            T !== null && (T = T.next = {
              lane: 0,
              revertLane: 0,
              gesture: null,
              action: z.action,
              hasEagerState: z.hasEagerState,
              eagerState: z.eagerState,
              next: null
            }), G === ha && (j = !0);
          else if ((rl & A) === A) {
            z = z.next, A === ha && (j = !0);
            continue;
          } else
            G = {
              lane: 0,
              revertLane: z.revertLane,
              gesture: null,
              action: z.action,
              hasEagerState: z.hasEagerState,
              eagerState: z.eagerState,
              next: null
            }, T === null ? (h = T = G, s = o) : T = T.next = G, wt.lanes |= A, Yl |= A;
          G = z.action, Sa && n(o, G), o = z.hasEagerState ? z.eagerState : n(o, G);
        } else
          A = {
            lane: G,
            revertLane: z.revertLane,
            gesture: z.gesture,
            action: z.action,
            hasEagerState: z.hasEagerState,
            eagerState: z.eagerState,
            next: null
          }, T === null ? (h = T = A, s = o) : T = T.next = A, wt.lanes |= G, Yl |= G;
        z = z.next;
      } while (z !== null && z !== e);
      if (T === null ? s = o : T.next = h, !$e(o, t.memoizedState) && (oe = !0, j && (n = ti, n !== null)))
        throw n;
      t.memoizedState = o, t.baseState = s, t.baseQueue = T, l.lastRenderedState = o;
    }
    return i === null && (l.lanes = 0), [t.memoizedState, l.dispatch];
  }
  function es(t) {
    var e = ne(), n = e.queue;
    if (n === null) throw Error(c(311));
    n.lastRenderedReducer = t;
    var l = n.dispatch, i = n.pending, o = e.memoizedState;
    if (i !== null) {
      n.pending = null;
      var s = i = i.next;
      do
        o = t(o, s.action), s = s.next;
      while (s !== i);
      $e(o, e.memoizedState) || (oe = !0), e.memoizedState = o, e.baseQueue === null && (e.baseState = o), n.lastRenderedState = o;
    }
    return [o, l];
  }
  function cv(t, e, n) {
    var l = wt, i = ne(), o = Ot;
    if (o) {
      if (n === void 0) throw Error(c(407));
      n = n();
    } else n = e();
    var s = !$e(
      (Xt || i).memoizedState,
      n
    );
    if (s && (i.memoizedState = n, oe = !0), i = i.queue, as(dv.bind(null, l, i, t), [
      t
    ]), t = i.getSnapshot !== e || s || ie !== null && (ie.memoizedState.tag & 1) !== 0, ii(
      t ? 9 : 8,
      { destroy: void 0 },
      fv.bind(null, l, i, n, e),
      null
    ), t) {
      if (l.flags |= 2048, kt === null) throw Error(c(349));
      o || (rl & 127) !== 0 || sv(l, e, n);
    }
    return n;
  }
  function sv(t, e, n) {
    t.flags |= 16384, t = { getSnapshot: e, value: n }, e = wt.updateQueue, e === null ? (e = Hu(), wt.updateQueue = e, e.stores = [t]) : (n = e.stores, n === null ? e.stores = [t] : n.push(t));
  }
  function fv(t, e, n, l) {
    e.value = n, e.getSnapshot = l, mv(e) && vv(t);
  }
  function dv(t, e, n) {
    return n(function() {
      mv(e) && vv(t);
    });
  }
  function mv(t) {
    var e = t.getSnapshot;
    t = t.value;
    try {
      var n = e();
      return !$e(t, n);
    } catch {
      return !0;
    }
  }
  function vv(t) {
    var e = ca(t, 2);
    e !== null && Ge(e, t, 2);
  }
  function ns(t) {
    var e = De();
    if (typeof t == "function") {
      var n = t;
      if (t = n(), Sa) {
        He(!0);
        try {
          n();
        } finally {
          He(!1);
        }
      }
    }
    return e.memoizedState = e.baseState = t, e.queue = {
      pending: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: cl,
      lastRenderedState: t
    }, e;
  }
  function hv(t, e, n, l) {
    return t.baseState = n, ts(
      t,
      Xt,
      typeof l == "function" ? l : cl
    );
  }
  function h1(t, e, n, l, i) {
    if (qu(t)) throw Error(c(485));
    if (t = e.action, t !== null) {
      var o = {
        payload: i,
        action: t,
        next: null,
        isTransition: !0,
        status: "pending",
        value: null,
        reason: null,
        listeners: [],
        then: function(s) {
          o.listeners.push(s);
        }
      };
      lt.T !== null ? n(!0) : o.isTransition = !1, l(o), n = e.pending, n === null ? (o.next = e.pending = o, gv(e, o)) : (o.next = n.next, e.pending = n.next = o);
    }
  }
  function gv(t, e) {
    var n = e.action, l = e.payload, i = t.state;
    if (e.isTransition) {
      var o = lt.T, s = {};
      s.types = o !== null ? o.types : null, lt.T = s;
      try {
        var h = n(i, l), T = lt.S;
        T !== null && T(s, h), yv(t, e, h);
      } catch (z) {
        ls(t, e, z);
      } finally {
        o !== null && s.types !== null && (o.types = s.types), lt.T = o;
      }
    } else
      try {
        o = n(i, l), yv(t, e, o);
      } catch (z) {
        ls(t, e, z);
      }
  }
  function yv(t, e, n) {
    n !== null && typeof n == "object" && typeof n.then == "function" ? n.then(
      function(l) {
        pv(t, e, l);
      },
      function(l) {
        return ls(t, e, l);
      }
    ) : pv(t, e, n);
  }
  function pv(t, e, n) {
    e.status = "fulfilled", e.value = n, bv(e), t.state = n, e = t.pending, e !== null && (n = e.next, n === e ? t.pending = null : (n = n.next, e.next = n, gv(t, n)));
  }
  function ls(t, e, n) {
    var l = t.pending;
    if (t.pending = null, l !== null) {
      l = l.next;
      do
        e.status = "rejected", e.reason = n, bv(e), e = e.next;
      while (e !== l);
    }
    t.action = null;
  }
  function bv(t) {
    t = t.listeners;
    for (var e = 0; e < t.length; e++) (0, t[e])();
  }
  function Sv(t, e) {
    return e;
  }
  function Ev(t, e) {
    if (Ot) {
      var n = kt.formState;
      if (n !== null) {
        t: {
          var l = wt;
          if (Ot) {
            if (Zt) {
              e: {
                for (var i = Zt, o = mn; i.nodeType !== 8; ) {
                  if (!o) {
                    i = null;
                    break e;
                  }
                  if (i = hn(
                    i.nextSibling
                  ), i === null) {
                    i = null;
                    break e;
                  }
                }
                o = i.data, i = o === "F!" || o === "F" ? i : null;
              }
              if (i) {
                Zt = hn(
                  i.nextSibling
                ), l = i.data === "F!";
                break t;
              }
            }
            _l(l);
          }
          l = !1;
        }
        l && (e = n[0]);
      }
    }
    return n = De(), n.memoizedState = n.baseState = e, l = {
      pending: null,
      lanes: 0,
      dispatch: null,
      lastRenderedReducer: Sv,
      lastRenderedState: e
    }, n.queue = l, n = qv.bind(
      null,
      wt,
      l
    ), l.dispatch = n, l = ns(!1), o = cs.bind(
      null,
      wt,
      !1,
      l.queue
    ), l = De(), i = {
      state: e,
      dispatch: null,
      action: t,
      pending: null
    }, l.queue = i, n = h1.bind(
      null,
      wt,
      i,
      o,
      n
    ), i.dispatch = n, l.memoizedState = t, [e, n, !1];
  }
  function xv(t) {
    var e = ne();
    return Tv(e, Xt, t);
  }
  function Tv(t, e, n) {
    if (e = ts(
      t,
      e,
      Sv
    )[0], t = Bu(cl)[0], typeof e == "object" && e !== null && typeof e.then == "function")
      try {
        var l = go(e);
      } catch (s) {
        throw s === ei ? _u : s;
      }
    else l = e;
    e = ne();
    var i = e.queue, o = i.dispatch;
    return n !== e.memoizedState && (wt.flags |= 2048, ii(
      9,
      { destroy: void 0 },
      g1.bind(null, i, n),
      null
    )), [l, o, t];
  }
  function g1(t, e) {
    t.action = e;
  }
  function wv(t) {
    var e = ne(), n = Xt;
    if (n !== null)
      return Tv(e, n, t);
    ne(), e = e.memoizedState, n = ne();
    var l = n.queue.dispatch;
    return n.memoizedState = t, [e, l, !1];
  }
  function ii(t, e, n, l) {
    return t = { tag: t, create: n, deps: l, inst: e, next: null }, e = wt.updateQueue, e === null && (e = Hu(), wt.updateQueue = e), n = e.lastEffect, n === null ? e.lastEffect = t.next = t : (l = n.next, n.next = t, t.next = l, e.lastEffect = t), t;
  }
  function Cv() {
    return ne().memoizedState;
  }
  function Lu(t, e, n, l) {
    var i = De();
    wt.flags |= t, i.memoizedState = ii(
      1 | e,
      { destroy: void 0 },
      n,
      l === void 0 ? null : l
    );
  }
  function Yu(t, e, n, l) {
    var i = ne();
    l = l === void 0 ? null : l;
    var o = i.memoizedState.inst;
    Xt !== null && l !== null && Jc(l, Xt.memoizedState.deps) ? i.memoizedState = ii(e, o, n, l) : (wt.flags |= t, i.memoizedState = ii(
      1 | e,
      o,
      n,
      l
    ));
  }
  function Ov(t, e) {
    Lu(8390656, 8, t, e);
  }
  function as(t, e) {
    Yu(2048, 8, t, e);
  }
  function y1(t) {
    wt.flags |= 4;
    var e = wt.updateQueue;
    if (e === null)
      e = Hu(), wt.updateQueue = e, e.events = [t];
    else {
      var n = e.events;
      n === null ? e.events = [t] : n.push(t);
    }
  }
  function _v(t) {
    var e = ne().memoizedState;
    return y1({ ref: e, nextImpl: t }), function() {
      if ((jt & 2) !== 0) throw Error(c(440));
      return e.impl.apply(void 0, arguments);
    };
  }
  function Av(t, e) {
    return Yu(4, 2, t, e);
  }
  function Rv(t, e) {
    return Yu(4, 4, t, e);
  }
  function Nv(t, e) {
    if (typeof e == "function") {
      t = t();
      var n = e(t);
      return function() {
        typeof n == "function" ? n() : e(null);
      };
    }
    if (e != null)
      return t = t(), e.current = t, function() {
        e.current = null;
      };
  }
  function Dv(t, e, n) {
    n = n != null ? n.concat([t]) : null, Yu(4, 4, Nv.bind(null, e, t), n);
  }
  function is() {
  }
  function zv(t, e) {
    var n = ne();
    e = e === void 0 ? null : e;
    var l = n.memoizedState;
    return e !== null && Jc(e, l[1]) ? l[0] : (n.memoizedState = [t, e], t);
  }
  function Mv(t, e) {
    var n = ne();
    e = e === void 0 ? null : e;
    var l = n.memoizedState;
    if (e !== null && Jc(e, l[1]))
      return l[0];
    if (l = t(), Sa) {
      He(!0);
      try {
        t();
      } finally {
        He(!1);
      }
    }
    return n.memoizedState = [l, e], l;
  }
  function os(t, e, n) {
    return n === void 0 || (rl & 1073741824) !== 0 && (Nt & 261930) === 0 ? t.memoizedState = e : (t.memoizedState = n, t = Xh(), wt.lanes |= t, Yl |= t, n);
  }
  function Uv(t, e, n, l) {
    return $e(n, e) ? n : Ml.current !== null ? (t = os(t, n, l), $e(t, e) || (oe = !0), t) : (rl & 106) === 0 || (rl & 1073741824) !== 0 && (Nt & 261930) === 0 ? (oe = !0, t.memoizedState = n) : (t = Xh(), wt.lanes |= t, Yl |= t, e);
  }
  function Hv(t, e, n, l, i) {
    var o = mt.p;
    mt.p = o !== 0 && 8 > o ? o : 8;
    var s = lt.T, h = {};
    h.types = s !== null ? s.types : null, lt.T = h, cs(t, !1, e, n);
    try {
      var T = i(), z = lt.S;
      if (z !== null && z(h, T), T !== null && typeof T == "object" && typeof T.then == "function") {
        var j = d1(
          T,
          l
        );
        yo(
          t,
          e,
          j,
          en(t)
        );
      } else
        yo(
          t,
          e,
          l,
          en(t)
        );
    } catch (G) {
      yo(
        t,
        e,
        { then: function() {
        }, status: "rejected", reason: G },
        en()
      );
    } finally {
      mt.p = o, s !== null && h.types !== null && (s.types = h.types), lt.T = s;
    }
  }
  function p1() {
  }
  function us(t, e, n, l) {
    if (t.tag !== 5) throw Error(c(476));
    var i = jv(t).queue;
    Hv(
      t,
      i,
      e,
      It,
      n === null ? p1 : function() {
        return Bv(t), n(l);
      }
    );
  }
  function jv(t) {
    var e = t.memoizedState;
    if (e !== null) return e;
    e = {
      memoizedState: It,
      baseState: It,
      baseQueue: null,
      queue: {
        pending: null,
        lanes: 0,
        dispatch: null,
        lastRenderedReducer: cl,
        lastRenderedState: It
      },
      next: null
    };
    var n = {};
    return e.next = {
      memoizedState: n,
      baseState: n,
      baseQueue: null,
      queue: {
        pending: null,
        lanes: 0,
        dispatch: null,
        lastRenderedReducer: cl,
        lastRenderedState: n
      },
      next: null
    }, t.memoizedState = e, t = t.alternate, t !== null && (t.memoizedState = e), e;
  }
  function Bv(t) {
    var e = jv(t);
    e.next === null && (e = t.alternate.memoizedState), yo(
      t,
      e.next.queue,
      {},
      en()
    );
  }
  function rs() {
    return be(wi);
  }
  function Lv() {
    return ne().memoizedState;
  }
  function Yv() {
    return ne().memoizedState;
  }
  function b1(t) {
    for (var e = t.return; e !== null; ) {
      switch (e.tag) {
        case 24:
        case 3:
          var n = en();
          t = Dl(n);
          var l = zl(e, t, n);
          l !== null && (Ge(l, e, n), so(l, e, n)), e = { cache: jc() }, t.payload = e;
          return;
      }
      e = e.return;
    }
  }
  function S1(t, e, n) {
    var l = en();
    n = {
      lane: l,
      revertLane: 0,
      gesture: null,
      action: n,
      hasEagerState: !1,
      eagerState: null,
      next: null
    }, qu(t) ? Vv(e, n) : (n = _c(t, e, n, l), n !== null && (Ge(n, t, l), Gv(n, e, l)));
  }
  function qv(t, e, n) {
    var l = en();
    yo(t, e, n, l);
  }
  function yo(t, e, n, l) {
    var i = {
      lane: l,
      revertLane: 0,
      gesture: null,
      action: n,
      hasEagerState: !1,
      eagerState: null,
      next: null
    };
    if (qu(t)) Vv(e, i);
    else {
      var o = t.alternate;
      if (t.lanes === 0 && (o === null || o.lanes === 0) && (o = e.lastRenderedReducer, o !== null))
        try {
          var s = e.lastRenderedState, h = o(s, n);
          if (i.hasEagerState = !0, i.eagerState = h, $e(h, s))
            return yu(t, e, i, 0), kt === null && gu(), !1;
        } catch {
        } finally {
        }
      if (n = _c(t, e, i, l), n !== null)
        return Ge(n, t, l), Gv(n, e, l), !0;
    }
    return !1;
  }
  function cs(t, e, n, l) {
    if (l = {
      lane: 2,
      revertLane: Ws(),
      gesture: null,
      action: l,
      hasEagerState: !1,
      eagerState: null,
      next: null
    }, qu(t)) {
      if (e) throw Error(c(479));
    } else
      e = _c(
        t,
        n,
        l,
        2
      ), e !== null && Ge(e, t, 2);
  }
  function qu(t) {
    var e = t.alternate;
    return t === wt || e !== null && e === wt;
  }
  function Vv(t, e) {
    li = Mu = !0;
    var n = t.pending;
    n === null ? e.next = e : (e.next = n.next, n.next = e), t.pending = e;
  }
  function Gv(t, e, n) {
    if ((n & 4194048) !== 0) {
      var l = e.lanes;
      l &= t.pendingLanes, n |= l, e.lanes = n, Xd(t, n);
    }
  }
  var Vu = {
    readContext: be,
    use: ju,
    useCallback: te,
    useContext: te,
    useEffect: te,
    useImperativeHandle: te,
    useLayoutEffect: te,
    useInsertionEffect: te,
    useMemo: te,
    useReducer: te,
    useRef: te,
    useState: te,
    useDebugValue: te,
    useDeferredValue: te,
    useTransition: te,
    useSyncExternalStore: te,
    useId: te,
    useHostTransitionStatus: te,
    useFormState: te,
    useActionState: te,
    useOptimistic: te,
    useMemoCache: te,
    useCacheRefresh: te,
    useEffectEvent: te
  }, Xv = {
    readContext: be,
    use: ju,
    useCallback: function(t, e) {
      return De().memoizedState = [
        t,
        e === void 0 ? null : e
      ], t;
    },
    useContext: be,
    useEffect: Ov,
    useImperativeHandle: function(t, e, n) {
      n = n != null ? n.concat([t]) : null, Lu(
        4194308,
        4,
        Nv.bind(null, e, t),
        n
      );
    },
    useLayoutEffect: function(t, e) {
      return Lu(4194308, 4, t, e);
    },
    useInsertionEffect: function(t, e) {
      Lu(4, 2, t, e);
    },
    useMemo: function(t, e) {
      var n = De();
      e = e === void 0 ? null : e;
      var l = t();
      if (Sa) {
        He(!0);
        try {
          t();
        } finally {
          He(!1);
        }
      }
      return n.memoizedState = [l, e], l;
    },
    useReducer: function(t, e, n) {
      var l = De();
      if (n !== void 0) {
        var i = n(e);
        if (Sa) {
          He(!0);
          try {
            n(e);
          } finally {
            He(!1);
          }
        }
      } else i = e;
      return l.memoizedState = l.baseState = i, t = {
        pending: null,
        lanes: 0,
        dispatch: null,
        lastRenderedReducer: t,
        lastRenderedState: i
      }, l.queue = t, t = t.dispatch = S1.bind(
        null,
        wt,
        t
      ), [l.memoizedState, t];
    },
    useRef: function(t) {
      var e = De();
      return t = { current: t }, e.memoizedState = t;
    },
    useState: function(t) {
      t = ns(t);
      var e = t.queue, n = qv.bind(null, wt, e);
      return e.dispatch = n, [t.memoizedState, n];
    },
    useDebugValue: is,
    useDeferredValue: function(t, e) {
      var n = De();
      return os(n, t, e);
    },
    useTransition: function() {
      var t = ns(!1);
      return t = Hv.bind(
        null,
        wt,
        t.queue,
        !0,
        !1
      ), De().memoizedState = t, [!1, t];
    },
    useSyncExternalStore: function(t, e, n) {
      var l = wt, i = De();
      if (Ot) {
        if (n === void 0)
          throw Error(c(407));
        n = n();
      } else {
        if (n = e(), kt === null)
          throw Error(c(349));
        (Nt & 127) !== 0 || sv(l, e, n);
      }
      i.memoizedState = n;
      var o = { value: n, getSnapshot: e };
      return i.queue = o, Ov(dv.bind(null, l, o, t), [
        t
      ]), l.flags |= 2048, ii(
        9,
        { destroy: void 0 },
        fv.bind(
          null,
          l,
          o,
          n,
          e
        ),
        null
      ), n;
    },
    useId: function() {
      var t = De(), e = kt.identifierPrefix;
      if (Ot) {
        var n = Mn, l = zn;
        n = (l & ~(1 << 32 - Ht(l) - 1)).toString(32) + n, e = "_" + e + "R_" + n, n = Uu++, 0 < n && (e += "H" + n.toString(32)), e += "_";
      } else
        n = m1++, e = "_" + e + "r_" + n.toString(32) + "_";
      return t.memoizedState = e;
    },
    useHostTransitionStatus: rs,
    useFormState: Ev,
    useActionState: Ev,
    useOptimistic: function(t) {
      var e = De();
      e.memoizedState = e.baseState = t;
      var n = {
        pending: null,
        lanes: 0,
        dispatch: null,
        lastRenderedReducer: null,
        lastRenderedState: null
      };
      return e.queue = n, e = cs.bind(
        null,
        wt,
        !0,
        n
      ), n.dispatch = e, [t, e];
    },
    useMemoCache: Wc,
    useCacheRefresh: function() {
      return De().memoizedState = b1.bind(
        null,
        wt
      );
    },
    useEffectEvent: function(t) {
      var e = De(), n = { impl: t };
      return e.memoizedState = n, function() {
        if ((jt & 2) !== 0)
          throw Error(c(440));
        return n.impl.apply(void 0, arguments);
      };
    }
  }, kv = {
    readContext: be,
    use: ju,
    useCallback: zv,
    useContext: be,
    useEffect: as,
    useImperativeHandle: Dv,
    useInsertionEffect: Av,
    useLayoutEffect: Rv,
    useMemo: Mv,
    useReducer: Bu,
    useRef: Cv,
    useState: function() {
      return Bu(cl);
    },
    useDebugValue: is,
    useDeferredValue: function(t, e) {
      var n = ne();
      return Uv(
        n,
        Xt.memoizedState,
        t,
        e
      );
    },
    useTransition: function() {
      var t = Bu(cl)[0], e = ne().memoizedState;
      return [
        typeof t == "boolean" ? t : go(t),
        e
      ];
    },
    useSyncExternalStore: cv,
    useId: Lv,
    useHostTransitionStatus: rs,
    useFormState: xv,
    useActionState: xv,
    useOptimistic: function(t, e) {
      var n = ne();
      return hv(n, Xt, t, e);
    },
    useMemoCache: Wc,
    useCacheRefresh: Yv,
    useEffectEvent: _v
  }, E1 = {
    readContext: be,
    use: ju,
    useCallback: zv,
    useContext: be,
    useEffect: as,
    useImperativeHandle: Dv,
    useInsertionEffect: Av,
    useLayoutEffect: Rv,
    useMemo: Mv,
    useReducer: es,
    useRef: Cv,
    useState: function() {
      return es(cl);
    },
    useDebugValue: is,
    useDeferredValue: function(t, e) {
      var n = ne();
      return Xt === null ? os(n, t, e) : Uv(
        n,
        Xt.memoizedState,
        t,
        e
      );
    },
    useTransition: function() {
      var t = es(cl)[0], e = ne().memoizedState;
      return [
        typeof t == "boolean" ? t : go(t),
        e
      ];
    },
    useSyncExternalStore: cv,
    useId: Lv,
    useHostTransitionStatus: rs,
    useFormState: wv,
    useActionState: wv,
    useOptimistic: function(t, e) {
      var n = ne();
      return Xt !== null ? hv(n, Xt, t, e) : (n.baseState = t, [t, n.queue.dispatch]);
    },
    useMemoCache: Wc,
    useCacheRefresh: Yv,
    useEffectEvent: _v
  };
  function ss(t, e, n, l) {
    e = t.memoizedState, n = n(l, e), n = n == null ? e : X({}, e, n), t.memoizedState = n, t.lanes === 0 && (t.updateQueue.baseState = n);
  }
  var fs = {
    enqueueSetState: function(t, e, n) {
      t = t._reactInternals;
      var l = en(), i = Dl(l);
      i.payload = e, n != null && (i.callback = n), e = zl(t, i, l), e !== null && (Ge(e, t, l), so(e, t, l));
    },
    enqueueReplaceState: function(t, e, n) {
      t = t._reactInternals;
      var l = en(), i = Dl(l);
      i.tag = 1, i.payload = e, n != null && (i.callback = n), e = zl(t, i, l), e !== null && (Ge(e, t, l), so(e, t, l));
    },
    enqueueForceUpdate: function(t, e) {
      t = t._reactInternals;
      var n = en(), l = Dl(n);
      l.tag = 2, e != null && (l.callback = e), e = zl(t, l, n), e !== null && (Ge(e, t, n), so(e, t, n));
    }
  };
  function Qv(t, e, n, l, i, o, s) {
    return t = t.stateNode, typeof t.shouldComponentUpdate == "function" ? t.shouldComponentUpdate(l, o, s) : e.prototype && e.prototype.isPureReactComponent ? !no(n, l) || !no(i, o) : !0;
  }
  function Zv(t, e, n, l) {
    t = e.state, typeof e.componentWillReceiveProps == "function" && e.componentWillReceiveProps(n, l), typeof e.UNSAFE_componentWillReceiveProps == "function" && e.UNSAFE_componentWillReceiveProps(n, l), e.state !== t && fs.enqueueReplaceState(e, e.state, null);
  }
  function Ea(t, e) {
    var n = e;
    if ("ref" in e) {
      n = {};
      for (var l in e)
        l !== "ref" && (n[l] = e[l]);
    }
    if (t = t.defaultProps) {
      n === e && (n = X({}, n));
      for (var i in t)
        n[i] === void 0 && (n[i] = t[i]);
    }
    return n;
  }
  function Kv(t) {
    hu(t);
  }
  function Jv(t) {
    console.error(t);
  }
  function Fv(t) {
    hu(t);
  }
  function Gu(t, e) {
    try {
      var n = t.onUncaughtError;
      n(e.value, { componentStack: e.stack });
    } catch (l) {
      setTimeout(function() {
        throw l;
      });
    }
  }
  function $v(t, e, n) {
    try {
      var l = t.onCaughtError;
      l(n.value, {
        componentStack: n.stack,
        errorBoundary: e.tag === 1 ? e.stateNode : null
      });
    } catch (i) {
      setTimeout(function() {
        throw i;
      });
    }
  }
  function ds(t, e, n) {
    return n = Dl(n), n.tag = 3, n.payload = { element: null }, n.callback = function() {
      Gu(t, e);
    }, n;
  }
  function Iv(t) {
    return t = Dl(t), t.tag = 3, t;
  }
  function Pv(t, e, n, l) {
    var i = n.type.getDerivedStateFromError;
    if (typeof i == "function") {
      var o = l.value;
      t.payload = function() {
        return i(o);
      }, t.callback = function() {
        $v(e, n, l);
      };
    }
    var s = n.stateNode;
    s !== null && typeof s.componentDidCatch == "function" && (t.callback = function() {
      $v(e, n, l), typeof i != "function" && (ql === null ? ql = /* @__PURE__ */ new Set([this]) : ql.add(this));
      var h = l.stack;
      this.componentDidCatch(l.value, {
        componentStack: h !== null ? h : ""
      });
    });
  }
  function x1(t, e, n, l, i) {
    if (n.flags |= 32768, l !== null && typeof l == "object" && typeof l.then == "function") {
      if (e = n.alternate, e !== null && ma(
        e,
        n,
        i,
        !0
      ), n = Se.current, n !== null) {
        switch (n.tag) {
          case 31:
          case 13:
          case 19:
            return Ce === null ? cr() : n.alternate === null && ee === 0 && (ee = 3), n.flags &= -257, n.flags |= 65536, n.lanes = i, l === Au ? n.flags |= 16384 : (e = n.updateQueue, e === null ? n.updateQueue = /* @__PURE__ */ new Set([l]) : e.add(l), $s(t, l, i)), !1;
          case 22:
            return n.flags |= 65536, l === Au ? n.flags |= 16384 : (e = n.updateQueue, e === null ? (e = {
              transitions: null,
              markerInstances: null,
              retryQueue: /* @__PURE__ */ new Set([l])
            }, n.updateQueue = e) : (n = e.retryQueue, n === null ? e.retryQueue = /* @__PURE__ */ new Set([l]) : n.add(l)), $s(t, l, i)), !1;
        }
        throw Error(c(435, n.tag));
      }
      return $s(t, l, i), cr(), !1;
    }
    if (Ot)
      return e = Se.current, e !== null ? ((e.flags & 65536) === 0 && (e.flags |= 256), e.flags |= 65536, e.lanes = i, l !== zc && (t = Error(c(422), { cause: l }), io(sn(t, n)))) : (l !== zc && (e = Error(c(423), {
        cause: l
      }), io(
        sn(e, n)
      )), t = t.current.alternate, t.flags |= 65536, i &= -i, t.lanes |= i, l = sn(l, n), i = ds(
        t.stateNode,
        l,
        i
      ), Gc(t, i), ee !== 4 && (ee = 2)), !1;
    var o = Error(c(520), { cause: l });
    if (o = sn(o, n), Co === null ? Co = [o] : Co.push(o), ee !== 4 && (ee = 2), e === null) return !0;
    l = sn(l, n), n = e;
    do {
      switch (n.tag) {
        case 3:
          return n.flags |= 65536, t = i & -i, n.lanes |= t, t = ds(n.stateNode, l, t), Gc(n, t), !1;
        case 1:
          if (e = n.type, o = n.stateNode, (n.flags & 128) === 0 && (typeof e.getDerivedStateFromError == "function" || o !== null && typeof o.componentDidCatch == "function" && (ql === null || !ql.has(o))))
            return n.flags |= 65536, i &= -i, n.lanes |= i, i = Iv(i), Pv(
              i,
              t,
              n,
              l
            ), Gc(n, i), !1;
          break;
        case 22:
          if (n.memoizedState !== null)
            return n.flags |= 65536, !1;
      }
      n = n.return;
    } while (n !== null);
    return !1;
  }
  var ms = Error(c(461)), oe = !1;
  function re(t, e, n, l) {
    e.child = t === null ? nv(e, null, n, l) : ba(
      e,
      t.child,
      n,
      l
    );
  }
  function Wv(t, e, n, l, i) {
    n = n.render;
    var o = e.ref;
    if ("ref" in l) {
      var s = {};
      for (var h in l)
        h !== "ref" && (s[h] = l[h]);
    } else s = l;
    return va(e), l = Fc(
      t,
      e,
      n,
      s,
      o,
      i
    ), h = $c(), t !== null && !oe ? (Ic(t, e, i), sl(t, e, i)) : (Ot && h && Eu(e), e.flags |= 1, re(t, e, l, i), e.child);
  }
  function th(t, e, n, l, i) {
    if (t === null) {
      var o = n.type;
      return typeof o == "function" && !Ac(o) && o.defaultProps === void 0 && n.compare === null ? (e.tag = 15, e.type = o, eh(
        t,
        e,
        o,
        l,
        i
      )) : (t = bu(
        n.type,
        null,
        l,
        e,
        e.mode,
        i
      ), t.ref = e.ref, t.return = e, e.child = t);
    }
    if (o = t.child, !Es(t, i)) {
      var s = o.memoizedProps;
      if (n = n.compare, n = n !== null ? n : no, n(s, l) && t.ref === e.ref)
        return sl(t, e, i);
    }
    return e.flags |= 1, t = al(o, l), t.ref = e.ref, t.return = e, e.child = t;
  }
  function eh(t, e, n, l, i) {
    if (t !== null) {
      var o = t.memoizedProps;
      if (no(o, l) && t.ref === e.ref)
        if (oe = !1, e.pendingProps = l = o, Es(t, i))
          (t.flags & 131072) !== 0 && (oe = !0);
        else
          return e.lanes = t.lanes, sl(t, e, i);
    }
    return vs(
      t,
      e,
      n,
      l,
      i
    );
  }
  function nh(t, e, n, l) {
    var i = l.children, o = t !== null ? t.memoizedState : null;
    if (t === null && e.stateNode === null && (e.stateNode = {
      _visibility: 1,
      _pendingMarkers: null,
      _retryCache: null,
      _transitions: null
    }), l.mode === "hidden") {
      if ((e.flags & 128) !== 0) {
        if (o = o !== null ? o.baseLanes | n : n, t !== null) {
          for (l = e.child = t.child, i = 0; l !== null; )
            i = i | l.lanes | l.childLanes, l = l.sibling;
          l = i & ~o;
        } else l = 0, e.child = null;
        return lh(
          t,
          e,
          o,
          n,
          l
        );
      }
      if ((n & 536870912) !== 0)
        e.memoizedState = { baseLanes: 0, cachePool: null }, t !== null && Ou(
          e,
          o !== null ? o.cachePool : null
        ), o !== null ? iv(e, o) : kc(), ov(e);
      else
        return l = e.lanes = 536870912, lh(
          t,
          e,
          o !== null ? o.baseLanes | n : n,
          n,
          l
        );
    } else
      o !== null ? (Ou(e, o.cachePool), iv(e, o), Hl(), e.memoizedState = null) : (t !== null && Ou(e, null), kc(), Hl());
    return re(t, e, i, n), e.child;
  }
  function po(t, e) {
    return t !== null && t.tag === 22 || e.stateNode !== null || (e.stateNode = {
      _visibility: 1,
      _pendingMarkers: null,
      _retryCache: null,
      _transitions: null
    }), e.sibling;
  }
  function lh(t, e, n, l, i) {
    var o = Lc();
    return o = o === null ? null : { parent: ae._currentValue, pool: o }, e.memoizedState = {
      baseLanes: n,
      cachePool: o
    }, t !== null && Ou(e, null), kc(), ov(e), t !== null && ma(t, e, l, !0), e.childLanes = i, null;
  }
  function Xu(t, e) {
    return e = ku(
      { mode: e.mode, children: e.children },
      t.mode
    ), e.ref = t.ref, t.child = e, e.return = t, e;
  }
  function ah(t, e, n) {
    return ba(e, t.child, null, n), t = Xu(e, e.pendingProps), t.flags |= 2, Ie(e), e.memoizedState = null, t;
  }
  function T1(t, e, n) {
    var l = e.pendingProps, i = (e.flags & 128) !== 0;
    if (e.flags &= -129, t === null) {
      if (Ot) {
        if (l.mode === "hidden")
          return t = Xu(e, l), e.lanes = 536870912, t.memoizedState = { baseLanes: 0, cachePool: null }, po(null, t);
        if (Zc(e), (t = Zt) ? (t = Ng(
          t,
          mn
        ), t = t !== null && t.data === "&" ? t : null, t !== null && (e.memoizedState = {
          dehydrated: t,
          treeContext: Cl !== null ? { id: zn, overflow: Mn } : null,
          retryLane: 536870912,
          hydrationErrors: null
        }, n = Vm(t), n.return = e, e.child = n, de = e, Zt = null)) : t = null, t === null) throw _l(e);
        return e.lanes = 536870912, null;
      }
      return Xu(e, l);
    }
    var o = t.memoizedState;
    if (o !== null) {
      var s = o.dehydrated;
      if (Zc(e), i)
        if (e.flags & 256)
          e.flags &= -257, e = ah(
            t,
            e,
            n
          );
        else if (e.memoizedState !== null)
          e.child = t.child, e.flags |= 128, e = null;
        else throw Error(c(558));
      else if (oe || ma(t, e, n, !1), i = (n & t.childLanes) !== 0, oe || i) {
        if (Ml.current === null) {
          if (l = kt, l !== null && (s = kd(l, n), s !== 0 && s !== o.retryLane))
            throw o.retryLane = s, ca(t, s), Ge(l, t, s), ms;
          cr();
        }
        e = ah(
          t,
          e,
          n
        );
      } else
        t = o.treeContext, Zt = hn(s.nextSibling), de = e, Ot = !0, Ol = null, mn = !1, t !== null && km(e, t), e = Xu(e, l), e.flags |= 134221824;
      return e;
    }
    return t = al(t.child, {
      mode: l.mode,
      children: l.children
    }), t.ref = e.ref, e.child = t, t.return = e, t;
  }
  function oi(t, e) {
    var n = e.ref;
    if (n === null)
      t !== null && t.ref !== null && (e.flags |= 4194816);
    else {
      if (typeof n != "function" && typeof n != "object")
        throw Error(c(284));
      (t === null || t.ref !== n) && (e.flags |= 4194816);
    }
  }
  function vs(t, e, n, l, i) {
    return va(e), n = Fc(
      t,
      e,
      n,
      l,
      void 0,
      i
    ), l = $c(), t !== null && !oe ? (Ic(t, e, i), sl(t, e, i)) : (Ot && l && Eu(e), e.flags |= 1, re(t, e, n, i), e.child);
  }
  function ih(t, e, n, l, i, o) {
    return va(e), e.updateQueue = null, n = rv(
      e,
      l,
      n,
      i
    ), uv(t), l = $c(), t !== null && !oe ? (Ic(t, e, o), sl(t, e, o)) : (Ot && l && Eu(e), e.flags |= 1, re(t, e, n, o), e.child);
  }
  function oh(t, e, n, l, i) {
    if (va(e), e.stateNode === null) {
      var o = $a, s = n.contextType;
      typeof s == "object" && s !== null && (o = be(s)), o = new n(l, o), e.memoizedState = o.state !== null && o.state !== void 0 ? o.state : null, o.updater = fs, e.stateNode = o, o._reactInternals = e, o = e.stateNode, o.props = l, o.state = e.memoizedState, o.refs = {}, qc(e), s = n.contextType, o.context = typeof s == "object" && s !== null ? be(s) : $a, o.state = e.memoizedState, s = n.getDerivedStateFromProps, typeof s == "function" && (ss(
        e,
        n,
        s,
        l
      ), o.state = e.memoizedState), typeof n.getDerivedStateFromProps == "function" || typeof o.getSnapshotBeforeUpdate == "function" || typeof o.UNSAFE_componentWillMount != "function" && typeof o.componentWillMount != "function" || (s = o.state, typeof o.componentWillMount == "function" && o.componentWillMount(), typeof o.UNSAFE_componentWillMount == "function" && o.UNSAFE_componentWillMount(), s !== o.state && fs.enqueueReplaceState(o, o.state, null), mo(e, l, o, i), fo(), o.state = e.memoizedState), typeof o.componentDidMount == "function" && (e.flags |= 4194308), l = !0;
    } else if (t === null) {
      o = e.stateNode;
      var h = e.memoizedProps, T = Ea(n, h);
      o.props = T;
      var z = o.context, j = n.contextType;
      s = $a, typeof j == "object" && j !== null && (s = be(j));
      var G = n.getDerivedStateFromProps;
      j = typeof G == "function" || typeof o.getSnapshotBeforeUpdate == "function", h = e.pendingProps !== h, j || typeof o.UNSAFE_componentWillReceiveProps != "function" && typeof o.componentWillReceiveProps != "function" || (h || z !== s) && Zv(
        e,
        o,
        l,
        s
      ), Nl = !1;
      var A = e.memoizedState;
      o.state = A, mo(e, l, o, i), fo(), z = e.memoizedState, h || A !== z || Nl ? (typeof G == "function" && (ss(
        e,
        n,
        G,
        l
      ), z = e.memoizedState), (T = Nl || Qv(
        e,
        n,
        T,
        l,
        A,
        z,
        s
      )) ? (j || typeof o.UNSAFE_componentWillMount != "function" && typeof o.componentWillMount != "function" || (typeof o.componentWillMount == "function" && o.componentWillMount(), typeof o.UNSAFE_componentWillMount == "function" && o.UNSAFE_componentWillMount()), typeof o.componentDidMount == "function" && (e.flags |= 4194308)) : (typeof o.componentDidMount == "function" && (e.flags |= 4194308), e.memoizedProps = l, e.memoizedState = z), o.props = l, o.state = z, o.context = s, l = T) : (typeof o.componentDidMount == "function" && (e.flags |= 4194308), l = !1);
    } else {
      o = e.stateNode, Vc(t, e), s = e.memoizedProps, j = Ea(n, s), o.props = j, G = e.pendingProps, A = o.context, z = n.contextType, T = $a, typeof z == "object" && z !== null && (T = be(z)), h = n.getDerivedStateFromProps, (z = typeof h == "function" || typeof o.getSnapshotBeforeUpdate == "function") || typeof o.UNSAFE_componentWillReceiveProps != "function" && typeof o.componentWillReceiveProps != "function" || (s !== G || A !== T) && Zv(
        e,
        o,
        l,
        T
      ), Nl = !1, A = e.memoizedState, o.state = A, mo(e, l, o, i), fo();
      var U = e.memoizedState;
      s !== G || A !== U || Nl || t !== null && t.dependencies !== null && wu(t.dependencies) ? (typeof h == "function" && (ss(
        e,
        n,
        h,
        l
      ), U = e.memoizedState), (j = Nl || Qv(
        e,
        n,
        j,
        l,
        A,
        U,
        T
      ) || t !== null && t.dependencies !== null && wu(t.dependencies)) ? (z || typeof o.UNSAFE_componentWillUpdate != "function" && typeof o.componentWillUpdate != "function" || (typeof o.componentWillUpdate == "function" && o.componentWillUpdate(l, U, T), typeof o.UNSAFE_componentWillUpdate == "function" && o.UNSAFE_componentWillUpdate(
        l,
        U,
        T
      )), typeof o.componentDidUpdate == "function" && (e.flags |= 4), typeof o.getSnapshotBeforeUpdate == "function" && (e.flags |= 1024)) : (typeof o.componentDidUpdate != "function" || s === t.memoizedProps && A === t.memoizedState || (e.flags |= 4), typeof o.getSnapshotBeforeUpdate != "function" || s === t.memoizedProps && A === t.memoizedState || (e.flags |= 1024), e.memoizedProps = l, e.memoizedState = U), o.props = l, o.state = U, o.context = T, l = j) : (typeof o.componentDidUpdate != "function" || s === t.memoizedProps && A === t.memoizedState || (e.flags |= 4), typeof o.getSnapshotBeforeUpdate != "function" || s === t.memoizedProps && A === t.memoizedState || (e.flags |= 1024), l = !1);
    }
    return o = l, oi(t, e), l = (e.flags & 128) !== 0, o || l ? (o = e.stateNode, n = l && typeof n.getDerivedStateFromError != "function" ? null : o.render(), e.flags |= 1, t !== null && l ? (e.child = ba(
      e,
      t.child,
      null,
      i
    ), e.child = ba(
      e,
      null,
      n,
      i
    )) : re(t, e, n, i), e.memoizedState = o.state, t = e.child) : t = sl(
      t,
      e,
      i
    ), t;
  }
  function uh(t, e, n, l) {
    return fa(), e.flags |= 256, re(t, e, n, l), e.child;
  }
  var hs = {
    dehydrated: null,
    treeContext: null,
    retryLane: 0,
    hydrationErrors: null
  };
  function gs(t) {
    return { baseLanes: t, cachePool: $m() };
  }
  function ys(t, e, n) {
    return t = t !== null ? t.childLanes & ~n : 0, e && (t |= tn), t;
  }
  function rh(t, e, n) {
    var l = e.pendingProps, i = !1, o = (e.flags & 128) !== 0, s;
    if ((s = o) || (s = t !== null && t.memoizedState === null ? !1 : (Ee.current & 2) !== 0), s && (i = !0, e.flags &= -129), s = (e.flags & 32) !== 0, e.flags &= -33, t === null) {
      if (Ot) {
        if (i ? Ul(e) : Hl(), (t = Zt) ? (t = Ng(
          t,
          mn
        ), t = t !== null && t.data !== "&" ? t : null, t !== null && (e.memoizedState = {
          dehydrated: t,
          treeContext: Cl !== null ? { id: zn, overflow: Mn } : null,
          retryLane: 536870912,
          hydrationErrors: null
        }, n = Vm(t), n.return = e, e.child = n, de = e, Zt = null)) : t = null, t === null) throw _l(e);
        return yf(t) ? e.lanes = 32 : e.lanes = 536870912, null;
      }
      return o = l.children, l = l.fallback, i ? (Hl(), i = e.mode, o = ku(
        { mode: "hidden", children: o },
        i
      ), l = sa(
        l,
        i,
        n,
        null
      ), o.return = e, l.return = e, o.sibling = l, e.child = o, l = e.child, l.memoizedState = gs(n), l.childLanes = ys(
        t,
        s,
        n
      ), e.memoizedState = hs, po(null, l)) : (Ul(e), ps(e, o));
    }
    var h = t.memoizedState;
    if (h !== null) {
      var T = h.dehydrated;
      if (T !== null)
        return w1(
          t,
          e,
          o,
          s,
          l,
          T,
          h,
          n
        );
    }
    return i ? (Hl(), i = l.fallback, o = e.mode, h = t.child, T = h.sibling, l = al(h, {
      mode: "hidden",
      children: l.children
    }), l.subtreeFlags = h.subtreeFlags & 1206910976, T !== null ? i = al(T, i) : (i = sa(
      i,
      o,
      n,
      null
    ), i.flags |= 2), i.return = e, l.return = e, l.sibling = i, e.child = l, po(null, l), l = e.child, i = t.child.memoizedState, i === null ? i = gs(n) : (o = i.cachePool, o !== null ? (h = ae._currentValue, o = o.parent !== h ? { parent: h, pool: h } : o) : o = $m(), i = {
      baseLanes: i.baseLanes | n,
      cachePool: o
    }), l.memoizedState = i, l.childLanes = ys(
      t,
      s,
      n
    ), e.memoizedState = hs, po(t.child, l)) : (Ul(e), n = t.child, t = n.sibling, n = al(n, {
      mode: "visible",
      children: l.children
    }), n.return = e, n.sibling = null, t !== null && (s = e.deletions, s === null ? (e.deletions = [t], e.flags |= 16) : s.push(t)), e.child = n, e.memoizedState = null, n);
  }
  function ps(t, e) {
    return e = ku(
      { mode: "visible", children: e },
      t.mode
    ), e.return = t, t.child = e;
  }
  function ku(t, e) {
    return t = Le(22, t, null, e), t.lanes = 0, t;
  }
  function Qu(t, e, n) {
    return ba(e, t.child, null, n), t = ps(
      e,
      e.pendingProps.children
    ), t.flags |= 2, e.memoizedState = null, t;
  }
  function w1(t, e, n, l, i, o, s, h) {
    if (n)
      return e.flags & 256 ? (Ul(e), e.flags &= -257, Qu(
        t,
        e,
        h
      )) : e.memoizedState !== null ? (Hl(), e.child = t.child, e.flags |= 128, null) : (Hl(), o = i.fallback, s = e.mode, i = ku(
        { mode: "visible", children: i.children },
        s
      ), o = sa(
        o,
        s,
        h,
        null
      ), o.flags |= 2, i.return = e, o.return = e, i.sibling = o, e.child = i, ba(e, t.child, null, h), i = e.child, i.memoizedState = gs(h), i.childLanes = ys(
        t,
        l,
        h
      ), e.memoizedState = hs, po(null, i));
    if (Ul(e), yf(o)) {
      if (l = o.nextSibling && o.nextSibling.dataset, l) var T = l.dgst;
      return l = T, l !== "" && (i = Error(c(419)), i.stack = "", i.digest = l, io({ value: i, source: null, stack: null })), Qu(
        t,
        e,
        h
      );
    }
    if (oe || ma(t, e, h, !1), l = (h & t.childLanes) !== 0, oe || l) {
      if (Ml.current !== null)
        return Qu(
          t,
          e,
          h
        );
      if (l = kt, l !== null && (i = kd(
        l,
        h
      ), i !== 0 && i !== s.retryLane))
        throw s.retryLane = i, ca(t, i), Ge(l, t, i), ms;
      return gf(o) || cr(), Qu(
        t,
        e,
        h
      );
    }
    return gf(o) ? (e.flags |= 192, e.child = t.child, null) : (t = s.treeContext, Zt = hn(o.nextSibling), de = e, Ot = !0, Ol = null, mn = !1, t !== null && km(e, t), e = ps(
      e,
      i.children
    ), e.flags |= 134221824, e);
  }
  function ch(t, e, n) {
    t.lanes |= e;
    var l = t.alternate;
    l !== null && (l.lanes |= e), Tu(t.return, e, n);
  }
  function sh(t) {
    for (var e = null; t !== null; ) {
      var n = t.alternate;
      n !== null && zu(n) === null && (e = t), t = t.sibling;
    }
    return e;
  }
  function Zu(t, e, n, l, i, o) {
    var s = t.memoizedState;
    s === null ? t.memoizedState = {
      isBackwards: e,
      rendering: null,
      renderingStartTime: 0,
      last: l,
      tail: n,
      tailMode: i,
      treeForkCount: o
    } : (s.isBackwards = e, s.rendering = null, s.renderingStartTime = 0, s.last = l, s.tail = n, s.tailMode = i, s.treeForkCount = o);
  }
  function bs(t) {
    var e = t.child;
    for (t.child = null; e !== null; ) {
      var n = e.sibling;
      e.sibling = t.child, t.child = e, e = n;
    }
  }
  function Ss(t, e, n) {
    var l = e.pendingProps, i = l.revealOrder, o = l.tail;
    l = l.children;
    var s = Ee.current;
    if (e.flags & 128)
      return vo(e, s), null;
    var h = (s & 2) !== 0;
    if (h ? (s = s & 1 | 2, e.flags |= 128) : s &= 1, vo(e, s), i === "backwards" && t !== null ? (bs(t), re(t, e, l, n), bs(t)) : re(t, e, l, n), l = Ot ? ao : 0, !h && t !== null && (t.flags & 128) !== 0)
      t: for (t = e.child; t !== null; ) {
        if (t.tag === 13)
          t.memoizedState !== null && ch(t, n, e);
        else if (t.tag === 19)
          ch(t, n, e);
        else if (t.child !== null) {
          t.child.return = t, t = t.child;
          continue;
        }
        if (t === e) break t;
        for (; t.sibling === null; ) {
          if (t.return === null || t.return === e)
            break t;
          t = t.return;
        }
        t.sibling.return = t.return, t = t.sibling;
      }
    switch (i) {
      case "backwards":
        n = sh(e.child), n === null ? (i = e.child, e.child = null) : (i = n.sibling, n.sibling = null, bs(e)), Zu(
          e,
          !0,
          i,
          null,
          o,
          l
        );
        break;
      case "unstable_legacy-backwards":
        for (n = null, i = e.child, e.child = null; i !== null; ) {
          if (t = i.alternate, t !== null && zu(t) === null) {
            e.child = i;
            break;
          }
          t = i.sibling, i.sibling = n, n = i, i = t;
        }
        Zu(
          e,
          !0,
          n,
          null,
          o,
          l
        );
        break;
      case "together":
        Zu(
          e,
          !1,
          null,
          null,
          void 0,
          l
        );
        break;
      case "independent":
        e.memoizedState = null;
        break;
      default:
        n = sh(e.child), n === null ? (i = e.child, e.child = null) : (i = n.sibling, n.sibling = null), Zu(
          e,
          !1,
          i,
          n,
          o,
          l
        );
    }
    return e.child;
  }
  function fh(t, e, n) {
    var l = e.pendingProps;
    return Al(e, e.type, l.value), re(t, e, l.children, n), e.child;
  }
  function sl(t, e, n) {
    if (t !== null && (e.dependencies = t.dependencies), Yl |= e.lanes, (n & e.childLanes) === 0)
      if (t !== null) {
        if (ma(
          t,
          e,
          n,
          !1
        ), (n & e.childLanes) === 0)
          return null;
      } else return null;
    if (t !== null && e.child !== t.child)
      throw Error(c(153));
    if (e.child !== null) {
      for (t = e.child, n = al(t, t.pendingProps), e.child = n, n.return = e; t.sibling !== null; )
        t = t.sibling, n = n.sibling = al(t, t.pendingProps), n.return = e;
      n.sibling = null;
    }
    return e.child;
  }
  function Es(t, e) {
    return (t.lanes & e) !== 0 ? !0 : (t = t.dependencies, !!(t !== null && wu(t)));
  }
  function C1(t, e, n) {
    switch (e.tag) {
      case 3:
        na(e, e.stateNode.containerInfo), Al(e, ae, t.memoizedState.cache), fa();
        break;
      case 27:
      case 5:
        Li(e);
        break;
      case 4:
        na(e, e.stateNode.containerInfo);
        break;
      case 10:
        Al(
          e,
          e.type,
          e.memoizedProps.value
        );
        break;
      case 31:
        if (e.memoizedState !== null)
          return e.flags |= 128, Zc(e), null;
        break;
      case 13:
        var l = e.memoizedState;
        if (l !== null) {
          if (l.dehydrated !== null)
            return Ul(e), e.flags |= 128, null;
          l = ma(
            t,
            e,
            n,
            !1
          );
          var i = e.child.childLanes;
          return l || (n & i) !== 0 ? rh(t, e, n) : (Ul(e), t = sl(
            t,
            e,
            n
          ), t !== null ? t.sibling : null);
        }
        Ul(e);
        break;
      case 19:
        if (e.flags & 128)
          return Ss(
            t,
            e,
            n
          );
        if (i = (t.flags & 128) !== 0, l = (n & e.childLanes) !== 0, l || (ma(
          t,
          e,
          n,
          !1
        ), l = (n & e.childLanes) !== 0), i) {
          if (l)
            return Ss(
              t,
              e,
              n
            );
          e.flags |= 128;
        }
        if (i = e.memoizedState, i !== null && (i.rendering = null, i.tail = null, i.lastEffect = null), vo(e, Ee.current), l) break;
        return null;
      case 22:
        return e.lanes = 0, nh(
          t,
          e,
          n,
          e.pendingProps
        );
      case 24:
        Al(e, ae, t.memoizedState.cache);
    }
    return sl(t, e, n);
  }
  function dh(t, e, n) {
    if (t !== null)
      if (t.memoizedProps !== e.pendingProps)
        oe = !0;
      else {
        if (!Es(t, n) && (e.flags & 128) === 0)
          return oe = !1, C1(
            t,
            e,
            n
          );
        oe = (t.flags & 131072) !== 0;
      }
    else
      oe = !1, Ot && (e.flags & 1048576) !== 0 && Xm(e, ao, e.index);
    switch (e.lanes = 0, e.tag) {
      case 16:
        t: {
          var l = e.pendingProps;
          if (t = ya(e.elementType), e.type = t, typeof t == "function")
            Ac(t) ? (l = Ea(t, l), e.tag = 1, e = oh(
              null,
              e,
              t,
              l,
              n
            )) : (e.tag = 0, e = vs(
              null,
              e,
              t,
              l,
              n
            ));
          else {
            if (t != null) {
              var i = t.$$typeof;
              if (i === B) {
                e.tag = 11, e = Wv(
                  null,
                  e,
                  t,
                  l,
                  n
                );
                break t;
              } else if (i === at) {
                e.tag = 14, e = th(
                  null,
                  e,
                  t,
                  l,
                  n
                );
                break t;
              } else if (i === yt) {
                e.tag = 10, e.type = t, e = fh(
                  null,
                  e,
                  n
                );
                break t;
              }
            }
            throw e = W(t) || t, Error(c(306, e, ""));
          }
        }
        return e;
      case 0:
        return vs(
          t,
          e,
          e.type,
          e.pendingProps,
          n
        );
      case 1:
        return l = e.type, i = Ea(
          l,
          e.pendingProps
        ), oh(
          t,
          e,
          l,
          i,
          n
        );
      case 3:
        t: {
          if (na(
            e,
            e.stateNode.containerInfo
          ), t === null) throw Error(c(387));
          l = e.pendingProps;
          var o = e.memoizedState;
          i = o.element, Vc(t, e), mo(e, l, null, n);
          var s = e.memoizedState;
          if (l = s.cache, Al(e, ae, l), l !== o.cache && Hc(
            e,
            [ae],
            n,
            !0
          ), fo(), l = s.element, o.isDehydrated)
            if (o = {
              element: l,
              isDehydrated: !1,
              cache: s.cache
            }, e.updateQueue.baseState = o, e.memoizedState = o, e.flags & 256) {
              e = uh(
                t,
                e,
                l,
                n
              );
              break t;
            } else if (l !== i) {
              i = sn(
                Error(c(424)),
                e
              ), io(i), e = uh(
                t,
                e,
                l,
                n
              );
              break t;
            } else {
              switch (t = e.stateNode.containerInfo, t.nodeType) {
                case 9:
                  t = t.body;
                  break;
                default:
                  t = t.nodeName === "HTML" ? t.ownerDocument.body : t;
              }
              for (Zt = hn(t.firstChild), de = e, Ot = !0, Ol = null, mn = !0, n = nv(
                e,
                null,
                l,
                n
              ), e.child = n; n; )
                n.flags = n.flags & -3 | 134221824, n = n.sibling;
            }
          else {
            if (fa(), l === i) {
              e = sl(
                t,
                e,
                n
              );
              break t;
            }
            re(t, e, l, n);
          }
          e = e.child;
        }
        return e;
      case 26:
        return oi(t, e), t === null ? (n = Bg(
          e.type,
          null,
          e.pendingProps,
          null
        )) ? e.memoizedState = n : Ot || (e.stateNode = gg(
          e.type,
          e.pendingProps,
          an.current,
          e
        )) : e.memoizedState = Bg(
          e.type,
          t.memoizedProps,
          e.pendingProps,
          t.memoizedState
        ), null;
      case 27:
        return Li(e), t === null && Ot && (l = e.stateNode = Mg(
          e.type,
          e.pendingProps,
          an.current
        ), de = e, mn = !0, i = Zt, Xl(e.type) ? (pf = i, Zt = hn(l.firstChild)) : Zt = i), re(
          t,
          e,
          e.pendingProps.children,
          n
        ), oi(t, e), t === null && (e.flags |= 4194304), e.child;
      case 5:
        return t === null && Ot && ((i = l = Zt) && (l = bS(
          l,
          e.type,
          e.pendingProps,
          mn
        ), l !== null ? (e.stateNode = l, de = e, Zt = hn(l.firstChild), mn = !1, i = !0) : i = !1), i || _l(e)), Li(e), i = e.type, o = e.pendingProps, s = t !== null ? t.memoizedProps : null, l = o.children, cf(i, o) ? l = null : s !== null && cf(i, s) && (e.flags |= 32), e.memoizedState !== null && (i = Fc(
          t,
          e,
          v1,
          null,
          null,
          n
        ), wi._currentValue = i), oi(t, e), re(t, e, l, n), e.child;
      case 6:
        return t === null && Ot && ((t = n = Zt) && (n = SS(
          n,
          e.pendingProps,
          mn
        ), n !== null ? (e.stateNode = n, de = e, Zt = null, t = !0) : t = !1), t || _l(e)), null;
      case 13:
        return rh(t, e, n);
      case 4:
        return na(
          e,
          e.stateNode.containerInfo
        ), l = e.pendingProps, t === null ? e.child = ba(
          e,
          null,
          l,
          n
        ) : re(t, e, l, n), e.child;
      case 11:
        return Wv(
          t,
          e,
          e.type,
          e.pendingProps,
          n
        );
      case 7:
        return l = e.pendingProps, oi(t, e), re(t, e, l, n), e.child;
      case 8:
        return re(
          t,
          e,
          e.pendingProps.children,
          n
        ), e.child;
      case 12:
        return re(
          t,
          e,
          e.pendingProps.children,
          n
        ), e.child;
      case 10:
        return fh(t, e, n);
      case 9:
        return i = e.type._context, l = e.pendingProps.children, va(e), i = be(i), l = l(i), e.flags |= 1, re(t, e, l, n), e.child;
      case 14:
        return th(
          t,
          e,
          e.type,
          e.pendingProps,
          n
        );
      case 15:
        return eh(
          t,
          e,
          e.type,
          e.pendingProps,
          n
        );
      case 19:
        return Ss(t, e, n);
      case 31:
        return T1(t, e, n);
      case 22:
        return nh(
          t,
          e,
          n,
          e.pendingProps
        );
      case 24:
        return va(e), l = be(ae), t === null ? (i = Lc(), i === null && (i = kt, o = jc(), i.pooledCache = o, o.refCount++, o !== null && (i.pooledCacheLanes |= n), i = o), e.memoizedState = { parent: l, cache: i }, qc(e), Al(e, ae, i)) : ((t.lanes & n) !== 0 && (Vc(t, e), mo(e, null, null, n), fo()), i = t.memoizedState, o = e.memoizedState, i.parent !== l ? (i = { parent: l, cache: l }, e.memoizedState = i, e.lanes === 0 && (e.memoizedState = e.updateQueue.baseState = i), Al(e, ae, l)) : (l = o.cache, Al(e, ae, l), l !== i.cache && Hc(
          e,
          [ae],
          n,
          !0
        ))), re(
          t,
          e,
          e.pendingProps.children,
          n
        ), e.child;
      case 30:
        return e.stateNode === null && (e.stateNode = {
          autoName: null,
          paired: null,
          clones: null,
          ref: null
        }), l = e.pendingProps, l.name != null && l.name !== "auto" ? e.flags |= t === null ? 18882560 : 18874368 : Ot && Eu(e), t !== null && t.memoizedProps.name !== l.name ? e.flags |= 4194816 : oi(t, e), re(t, e, l.children, n), e.child;
      case 29:
        throw e.pendingProps;
    }
    throw Error(c(156, e.tag));
  }
  function fl(t) {
    t.flags |= 4;
  }
  function xs(t, e, n, l, i) {
    var o;
    if ((o = (t.mode & 32) !== 0) && (o = n === null ? Vg(e, l) : Vg(e, l) && (l.src !== n.src || l.srcSet !== n.srcSet)), o) {
      if (t.flags |= 16777216, (i & 335544128) === i)
        if (t.stateNode.complete) t.flags |= 8192;
        else if (Kh()) t.flags |= 8192;
        else
          throw pa = Au, Yc;
    } else t.flags &= -16777217;
  }
  function mh(t, e) {
    if (e.type !== "stylesheet" || (e.state.loading & 4) !== 0)
      t.flags &= -16777217;
    else if (t.flags |= 16777216, !Gg(e))
      if (Kh()) t.flags |= 8192;
      else
        throw pa = Au, Yc;
  }
  function Ku(t, e) {
    e !== null && (t.flags |= 4), t.flags & 16384 && (e = t.tag !== 22 ? Vd() : 536870912, t.lanes |= e, fi |= e);
  }
  function bo(t, e) {
    if (!Ot)
      switch (t.tailMode) {
        case "visible":
          break;
        case "collapsed":
          for (var n = t.tail, l = null; n !== null; )
            n.alternate !== null && (l = n), n = n.sibling;
          l === null ? e || t.tail === null ? t.tail = null : t.tail.sibling = null : l.sibling = null;
          break;
        default:
          for (e = t.tail, n = null; e !== null; )
            e.alternate !== null && (n = e), e = e.sibling;
          n === null ? t.tail = null : n.sibling = null;
      }
  }
  function Kt(t) {
    var e = t.alternate !== null && t.alternate.child === t.child, n = 0, l = 0;
    if (e)
      for (var i = t.child; i !== null; )
        n |= i.lanes | i.childLanes, l |= i.subtreeFlags & 1206910976, l |= i.flags & 1206910976, i.return = t, i = i.sibling;
    else
      for (i = t.child; i !== null; )
        n |= i.lanes | i.childLanes, l |= i.subtreeFlags, l |= i.flags, i.return = t, i = i.sibling;
    return t.subtreeFlags |= l, t.childLanes = n, e;
  }
  function O1(t, e, n) {
    var l = e.pendingProps;
    switch (Dc(e), e.tag) {
      case 16:
      case 15:
      case 0:
      case 11:
      case 7:
      case 8:
      case 12:
      case 9:
      case 14:
        return Kt(e), null;
      case 1:
        return Kt(e), null;
      case 3:
        return n = e.stateNode, l = null, t !== null && (l = t.memoizedState.cache), e.memoizedState.cache !== l && (e.flags |= 2048), ul(ae), Je(), n.pendingContext && (n.context = n.pendingContext, n.pendingContext = null), (t === null || t.child === null) && (Wa(e) ? fl(e) : t === null || t.memoizedState.isDehydrated && (e.flags & 256) === 0 || (e.flags |= 1024, Mc())), Kt(e), null;
      case 26:
        var i = e.type, o = e.memoizedState;
        return t === null ? (fl(e), o !== null ? (Kt(e), mh(e, o)) : (Kt(e), xs(
          e,
          i,
          null,
          l,
          n
        ))) : o ? o !== t.memoizedState ? (fl(e), Kt(e), mh(e, o)) : (Kt(e), e.flags &= -16777217) : (t = t.memoizedProps, t !== l && fl(e), Kt(e), xs(
          e,
          i,
          t,
          l,
          n
        )), null;
      case 27:
        if (Ha(e), n = an.current, i = e.type, t !== null && e.stateNode != null)
          t.memoizedProps !== l && fl(e);
        else {
          if (!l) {
            if (e.stateNode === null)
              throw Error(c(166));
            return Kt(e), e.subtreeFlags &= -33554433, null;
          }
          t = Pt.current, Wa(e) ? Qm(e) : (t = Mg(i, l, n), e.stateNode = t, fl(e));
        }
        return Kt(e), e.subtreeFlags &= -33554433, null;
      case 5:
        if (Ha(e), i = e.type, t !== null && e.stateNode != null)
          t.memoizedProps !== l && fl(e);
        else {
          if (!l) {
            if (e.stateNode === null)
              throw Error(c(166));
            return Kt(e), e.subtreeFlags &= -33554433, null;
          }
          if (o = Pt.current, Wa(e))
            Qm(e);
          else {
            var s = No(
              an.current
            );
            switch (o) {
              case 1:
                o = s.createElementNS(
                  "http://www.w3.org/2000/svg",
                  i
                );
                break;
              case 2:
                o = s.createElementNS(
                  "http://www.w3.org/1998/Math/MathML",
                  i
                );
                break;
              default:
                switch (i) {
                  case "svg":
                    o = s.createElementNS(
                      "http://www.w3.org/2000/svg",
                      i
                    );
                    break;
                  case "math":
                    o = s.createElementNS(
                      "http://www.w3.org/1998/Math/MathML",
                      i
                    );
                    break;
                  case "script":
                    o = s.createElement("div"), o.innerHTML = "<script><\/script>", o = o.removeChild(
                      o.firstChild
                    );
                    break;
                  case "select":
                    o = typeof l.is == "string" ? s.createElement("select", {
                      is: l.is
                    }) : s.createElement("select"), l.multiple ? o.multiple = !0 : l.size && (o.size = l.size);
                    break;
                  default:
                    o = typeof l.is == "string" ? s.createElement(i, { is: l.is }) : s.createElement(i);
                }
            }
            o[pe] = e, o[Be] = l;
            t: for (s = e.child; s !== null; ) {
              if (s.tag === 5 || s.tag === 6)
                o.appendChild(s.stateNode);
              else if (s.tag !== 4 && s.tag !== 27 && s.child !== null) {
                s.child.return = s, s = s.child;
                continue;
              }
              if (s === e) break t;
              for (; s.sibling === null; ) {
                if (s.return === null || s.return === e)
                  break t;
                s = s.return;
              }
              s.sibling.return = s.return, s = s.sibling;
            }
            e.stateNode = o;
            t: switch (Te(o, i, l), i) {
              case "button":
              case "input":
              case "select":
              case "textarea":
                l = !!l.autoFocus;
                break t;
              case "img":
                l = !0;
                break t;
              default:
                l = !1;
            }
            l && fl(e);
          }
        }
        return Kt(e), e.subtreeFlags &= -33554433, xs(
          e,
          e.type,
          t === null ? null : t.memoizedProps,
          e.pendingProps,
          n
        ), null;
      case 6:
        if (t && e.stateNode != null)
          t.memoizedProps !== l && fl(e);
        else {
          if (typeof l != "string" && e.stateNode === null)
            throw Error(c(166));
          if (t = an.current, Wa(e)) {
            if (t = e.stateNode, n = e.memoizedProps, l = null, i = de, i !== null)
              switch (i.tag) {
                case 27:
                case 5:
                  l = i.memoizedProps;
              }
            t[pe] = e, t = !!(t.nodeValue === n || l !== null && l.suppressHydrationWarning === !0 || dg(t.nodeValue, n)), t || _l(e, !0);
          } else
            t = No(t).createTextNode(
              l
            ), t[pe] = e, e.stateNode = t;
        }
        return Kt(e), null;
      case 31:
        if (n = e.memoizedState, t === null || t.memoizedState !== null) {
          if (l = Wa(e), n !== null) {
            if (t === null) {
              if (!l) throw Error(c(318));
              if (t = e.memoizedState, t = t !== null ? t.dehydrated : null, !t) throw Error(c(557));
              t[pe] = e;
            } else
              fa(), (e.flags & 128) === 0 && (e.memoizedState = null), e.flags |= 4;
            Kt(e), t = !1;
          } else
            n = Mc(), t !== null && t.memoizedState !== null && (t.memoizedState.hydrationErrors = n), t = !0;
          if (!t)
            return e.flags & 256 ? (Ie(e), e) : (Ie(e), null);
          if ((e.flags & 128) !== 0)
            throw Error(c(558));
        }
        return Kt(e), null;
      case 13:
        if (l = e.memoizedState, t === null || t.memoizedState !== null && t.memoizedState.dehydrated !== null) {
          if (i = Wa(e), l !== null && l.dehydrated !== null) {
            if (t === null) {
              if (!i) throw Error(c(318));
              if (i = e.memoizedState, i = i !== null ? i.dehydrated : null, !i) throw Error(c(317));
              i[pe] = e;
            } else
              fa(), (e.flags & 128) === 0 && (e.memoizedState = null), e.flags |= 4;
            Kt(e), i = !1;
          } else
            i = Mc(), t !== null && t.memoizedState !== null && (t.memoizedState.hydrationErrors = i), i = !0;
          if (!i)
            return e.flags & 256 ? (Ie(e), e) : (Ie(e), null);
        }
        return Ie(e), (e.flags & 128) !== 0 ? (e.lanes = n, e) : (n = l !== null, t = t !== null && t.memoizedState !== null, n && (l = e.child, i = null, l.alternate !== null && l.alternate.memoizedState !== null && l.alternate.memoizedState.cachePool !== null && (i = l.alternate.memoizedState.cachePool.pool), o = null, l.memoizedState !== null && l.memoizedState.cachePool !== null && (o = l.memoizedState.cachePool.pool), o !== i && (l.flags |= 2048)), n !== t && n && (e.child.flags |= 8192), Ku(e, e.updateQueue), Kt(e), null);
      case 4:
        return Je(), t === null && lf(e.stateNode.containerInfo), e.flags |= 67108864, Kt(e), null;
      case 10:
        return ul(e.type), Kt(e), null;
      case 19:
        if (Kc(e), l = e.memoizedState, l === null) return Kt(e), null;
        if (i = (e.flags & 128) !== 0, o = l.rendering, o === null)
          if (i) bo(l, !1);
          else {
            if (ee !== 0 || t !== null && (t.flags & 128) !== 0)
              for (t = e.child; t !== null; ) {
                if (o = zu(t), o !== null) {
                  for (e.flags |= 128, bo(l, !1), t = o.updateQueue, e.updateQueue = t, Ku(e, t), e.subtreeFlags = 0, t = n, n = e.child; n !== null; )
                    qm(n, t), n = n.sibling;
                  return vo(
                    e,
                    Ee.current & 1 | 2
                  ), Ot && il(e, l.treeForkCount), e.child;
                }
                t = t.sibling;
              }
            l.tail !== null && Ae() > ir && (e.flags |= 128, i = !0, bo(l, !1), e.lanes = 4194304);
          }
        else {
          if (!i)
            if (t = zu(o), t !== null) {
              if (e.flags |= 128, i = !0, t = t.updateQueue, e.updateQueue = t, Ku(e, t), bo(l, !0), l.tail === null && l.tailMode !== "collapsed" && l.tailMode !== "visible" && !o.alternate && !Ot)
                return Kt(e), null;
            } else
              2 * Ae() - l.renderingStartTime > ir && n !== 536870912 && (e.flags |= 128, i = !0, bo(l, !1), e.lanes = 4194304);
          l.isBackwards ? (o.sibling = e.child, e.child = o) : (t = l.last, t !== null ? t.sibling = o : e.child = o, l.last = o);
        }
        if (l.tail !== null) {
          t = l.tail;
          t: {
            for (n = t; n !== null; ) {
              if (n.alternate !== null) {
                n = !1;
                break t;
              }
              n = n.sibling;
            }
            n = !0;
          }
          return l.rendering = t, l.tail = t.sibling, l.renderingStartTime = Ae(), t.sibling = null, o = Ee.current, o = i ? o & 1 | 2 : o & 1, l.tailMode === "visible" || l.tailMode === "collapsed" || !n || Ot ? vo(e, o) : (n = o, Ut(Se, e), Ut(Ee, n), Ce === null && (Ce = e)), Ot && il(e, l.treeForkCount), t;
        }
        return Kt(e), null;
      case 22:
      case 23:
        return Ie(e), Qc(), l = e.memoizedState !== null, t !== null ? t.memoizedState !== null !== l && (e.flags |= 8192) : l && (e.flags |= 8192), l ? (n & 536870912) !== 0 && (e.flags & 128) === 0 && (Kt(e), e.subtreeFlags & 6 && (e.flags |= 8192)) : Kt(e), n = e.updateQueue, n !== null && Ku(e, n.retryQueue), n = null, t !== null && t.memoizedState !== null && t.memoizedState.cachePool !== null && (n = t.memoizedState.cachePool.pool), l = null, e.memoizedState !== null && e.memoizedState.cachePool !== null && (l = e.memoizedState.cachePool.pool), l !== n && (e.flags |= 2048), t !== null && Qt(ga), null;
      case 24:
        return n = null, t !== null && (n = t.memoizedState.cache), e.memoizedState.cache !== n && (e.flags |= 2048), ul(ae), Kt(e), null;
      case 25:
        return null;
      case 30:
        return e.flags |= 33554432, Kt(e), null;
    }
    throw Error(c(156, e.tag));
  }
  function _1(t, e) {
    switch (Dc(e), e.tag) {
      case 1:
        return t = e.flags, t & 65536 ? (e.flags = t & -65537 | 128, e) : null;
      case 3:
        return ul(ae), Je(), t = e.flags, (t & 65536) !== 0 && (t & 128) === 0 ? (e.flags = t & -65537 | 128, e) : null;
      case 26:
      case 27:
      case 5:
        return Ha(e), null;
      case 31:
        if (e.memoizedState !== null) {
          if (Ie(e), e.alternate === null)
            throw Error(c(340));
          fa();
        }
        return t = e.flags, t & 65536 ? (e.flags = t & -65537 | 128, e) : null;
      case 13:
        if (Ie(e), t = e.memoizedState, t !== null && t.dehydrated !== null) {
          if (e.alternate === null)
            throw Error(c(340));
          fa();
        }
        return t = e.flags, t & 65536 ? (e.flags = t & -65537 | 128, e) : null;
      case 19:
        return Kc(e), t = e.flags, t & 65536 ? (e.flags = t & -65537 | 128, t = e.memoizedState, t !== null && (t.rendering = null, t.tail = null), e.flags |= 4, e) : null;
      case 4:
        return Je(), null;
      case 10:
        return ul(e.type), null;
      case 22:
      case 23:
        return Ie(e), Qc(), t !== null && Qt(ga), t = e.flags, t & 65536 ? (e.flags = t & -65537 | 128, e) : null;
      case 24:
        return ul(ae), null;
      case 25:
        return null;
      default:
        return null;
    }
  }
  function vh(t, e) {
    switch (Dc(e), e.tag) {
      case 3:
        ul(ae), Je();
        break;
      case 26:
      case 27:
      case 5:
        Ha(e);
        break;
      case 4:
        Je();
        break;
      case 31:
        e.memoizedState !== null && Ie(e);
        break;
      case 13:
        Ie(e);
        break;
      case 19:
        Kc(e);
        break;
      case 10:
        ul(e.type);
        break;
      case 22:
      case 23:
        Ie(e), Qc(), t !== null && Qt(ga);
        break;
      case 24:
        ul(ae);
    }
  }
  function So(t, e) {
    try {
      var n = e.updateQueue, l = n !== null ? n.lastEffect : null;
      if (l !== null) {
        var i = l.next;
        n = i;
        do {
          if ((n.tag & t) === t) {
            l = void 0;
            var o = n.create, s = n.inst;
            l = o(), s.destroy = l;
          }
          n = n.next;
        } while (n !== i);
      }
    } catch (h) {
      qt(e, e.return, h);
    }
  }
  function jl(t, e, n) {
    try {
      var l = e.updateQueue, i = l !== null ? l.lastEffect : null;
      if (i !== null) {
        var o = i.next;
        l = o;
        do {
          if ((l.tag & t) === t) {
            var s = l.inst, h = s.destroy;
            if (h !== void 0) {
              s.destroy = void 0, i = e;
              var T = n, z = h;
              try {
                z();
              } catch (j) {
                qt(
                  i,
                  T,
                  j
                );
              }
            }
          }
          l = l.next;
        } while (l !== o);
      }
    } catch (j) {
      qt(e, e.return, j);
    }
  }
  function hh(t) {
    var e = t.updateQueue;
    if (e !== null) {
      var n = t.stateNode;
      try {
        av(e, n);
      } catch (l) {
        qt(t, t.return, l);
      }
    }
  }
  function gh(t, e, n) {
    n.props = Ea(
      t.type,
      t.memoizedProps
    ), n.state = t.memoizedState;
    try {
      n.componentWillUnmount();
    } catch (l) {
      qt(t, e, l);
    }
  }
  function Un(t, e) {
    try {
      var n = t.ref;
      if (n !== null) {
        switch (t.tag) {
          case 26:
          case 27:
          case 5:
            var l = t.stateNode;
            break;
          case 30:
            var i = t.stateNode, o = nl(t.memoizedProps, i);
            (i.ref === null || i.ref.name !== o) && (i.ref = Tg(o)), l = i.ref;
            break;
          case 7:
            if (t.stateNode === null) {
              var s = new nn(t);
              d(
                t.child,
                !1,
                yS,
                s,
                void 0,
                void 0
              ), t.stateNode = s;
            }
            l = t.stateNode;
            break;
          default:
            l = t.stateNode;
        }
        typeof n == "function" ? t.refCleanup = n(l) : n.current = l;
      }
    } catch (h) {
      qt(t, e, h);
    }
  }
  function xe(t, e) {
    var n = t.ref, l = t.refCleanup;
    if (n !== null)
      if (typeof l == "function")
        try {
          l();
        } catch (i) {
          qt(t, e, i);
        } finally {
          t.refCleanup = null, t = t.alternate, t != null && (t.refCleanup = null);
        }
      else if (typeof n == "function")
        try {
          n(null);
        } catch (i) {
          qt(t, e, i);
        }
      else n.current = null;
  }
  function Ju(t, e) {
    if ((t.tag === 5 || t.tag === 27 || t.tag === 6) && t.alternate === null && e !== null)
      for (var n = 0; n < e.length; n++)
        Rg(
          t.stateNode,
          e[n]
        );
  }
  function yh(t) {
    for (var e = t.return; e !== null && (ws(e) && Rg(t.stateNode, e.stateNode), !Ts(e)); )
      e = e.return;
  }
  function Eo(t) {
    for (var e = t.return; e !== null && (ws(e) && pS(t.stateNode, e.stateNode), !Ts(e)); )
      e = e.return;
  }
  function Ts(t) {
    return t.tag === 5 || t.tag === 3 || t.tag === 27;
  }
  function ws(t) {
    return t && t.tag === 7 && t.stateNode !== null;
  }
  function Cs(t) {
    var e = t.type, n = t.memoizedProps, l = t.stateNode;
    try {
      t: switch (e) {
        case "button":
        case "input":
        case "select":
        case "textarea":
          n.autoFocus && l.focus();
          break t;
        case "img":
          n.src ? l.src = n.src : n.srcSet && (l.srcset = n.srcSet);
      }
    } catch (i) {
      qt(t, t.return, i);
    }
  }
  function Os(t, e, n) {
    try {
      var l = t.stateNode;
      W1(l, t.type, n, e), l[Be] = e;
    } catch (i) {
      qt(t, t.return, i);
    }
  }
  function ph(t) {
    return t.tag === 5 || t.tag === 3 || t.tag === 26 || t.tag === 27 && Xl(t.type) || t.tag === 4;
  }
  function _s(t) {
    t: for (; ; ) {
      for (; t.sibling === null; ) {
        if (t.return === null || ph(t.return)) return null;
        t = t.return;
      }
      for (t.sibling.return = t.return, t = t.sibling; t.tag !== 5 && t.tag !== 6 && t.tag !== 18; ) {
        if (t.tag === 27 && Xl(t.type) || t.flags & 2 || t.child === null || t.tag === 4) continue t;
        t.child.return = t, t = t.child;
      }
      if (!(t.flags & 2)) return t.stateNode;
    }
  }
  function As(t, e, n, l) {
    var i = t.tag;
    if (i === 5 || i === 6)
      i = t.stateNode, e ? (n.nodeType === 9 ? n.body : n.nodeName === "HTML" ? n.ownerDocument.body : n).insertBefore(i, e) : (e = n.nodeType === 9 ? n.body : n.nodeName === "HTML" ? n.ownerDocument.body : n, e.appendChild(i), n = n._reactRootContainer, n != null || e.onclick !== null || (e.onclick = Dn)), Ju(t, l), Mt = !0;
    else if (i !== 4 && (i === 27 && (Ju(t, l), l = null, Xl(t.type) && (n = t.stateNode, e = null)), t = t.child, t !== null))
      for (As(
        t,
        e,
        n,
        l
      ), t = t.sibling; t !== null; )
        As(
          t,
          e,
          n,
          l
        ), t = t.sibling;
  }
  function Fu(t, e, n, l) {
    var i = t.tag;
    if (i === 5 || i === 6)
      i = t.stateNode, e ? n.insertBefore(i, e) : n.appendChild(i), Ju(t, l), Mt = !0;
    else if (i !== 4 && (i === 27 && (Ju(t, l), l = null, Xl(t.type) && (n = t.stateNode)), t = t.child, t !== null))
      for (Fu(
        t,
        e,
        n,
        l
      ), t = t.sibling; t !== null; )
        Fu(
          t,
          e,
          n,
          l
        ), t = t.sibling;
  }
  function bh(t) {
    var e = t.stateNode, n = t.memoizedProps;
    try {
      for (var l = t.type, i = e.attributes; i.length; )
        e.removeAttributeNode(i[0]);
      Te(e, l, n), e[pe] = t, e[Be] = n;
    } catch (o) {
      qt(t, t.return, o);
    }
  }
  var $u = !1, Pe = null;
  function Sh(t) {
    (t.tag === 30 || (t.subtreeFlags & 33554432) !== 0) && ($u = !0);
  }
  var Hn = null;
  function Eh() {
    var t = Hn;
    return Hn = null, t;
  }
  var Ye = 0;
  function ui(t, e, n, l, i) {
    return Ye = 0, xh(
      t.child,
      e,
      n,
      l,
      i
    );
  }
  function xh(t, e, n, l, i) {
    for (var o = !1; t !== null; ) {
      if (t.tag === 5) {
        var s = t.stateNode;
        if (l !== null) {
          var h = df(s);
          l.push(h), h.view && (o = !0);
        } else
          o || df(s).view && (o = !0);
        $u = !0, Eg(
          s,
          Ye === 0 ? e : e + "_" + Ye,
          n
        ), Ye++;
      } else (t.tag !== 22 || t.memoizedState === null) && (t.tag === 30 && i || xh(
        t.child,
        e,
        n,
        l,
        i
      ) && (o = !0));
      t = t.sibling;
    }
    return o;
  }
  function jn(t, e) {
    for (; t !== null; )
      t.tag === 5 ? xg(t.stateNode, t.memoizedProps) : (t.tag !== 22 || t.memoizedState === null) && (t.tag === 30 && e || jn(
        t.child,
        e
      )), t = t.sibling;
  }
  function Iu(t) {
    if ((t.subtreeFlags & 18874368) !== 0)
      for (t = t.child; t !== null; ) {
        if ((t.tag !== 22 || t.memoizedState === null) && (Iu(t), t.tag === 30 && (t.flags & 18874368) !== 0 && t.stateNode.paired)) {
          var e = t.memoizedProps;
          if (e.name == null || e.name === "auto")
            throw Error(c(544));
          var n = e.name;
          e = ll(e.default, e.share), e !== "none" && (ui(
            t,
            n,
            e,
            null,
            !1
          ) || jn(t.child, !1));
        }
        t = t.sibling;
      }
  }
  function Rs(t, e) {
    if (t.tag === 30) {
      var n = t.stateNode, l = t.memoizedProps, i = nl(l, n), o = ll(
        l.default,
        n.paired ? l.share : l.enter
      );
      o !== "none" ? ui(t, i, o, null, !1) ? (Iu(t), n.paired || e || hi(t, l.onEnter)) : jn(t.child, !1) : Iu(t);
    } else if ((t.subtreeFlags & 33554432) !== 0)
      for (t = t.child; t !== null; )
        Rs(t, e), t = t.sibling;
    else Iu(t);
  }
  function Ns(t) {
    if (Pe !== null && Pe.size !== 0) {
      var e = Pe;
      if ((t.subtreeFlags & 18874368) !== 0)
        for (t = t.child; t !== null; ) {
          if (t.tag !== 22 || t.memoizedState === null) {
            if (t.tag === 30 && (t.flags & 18874368) !== 0) {
              var n = t.memoizedProps, l = n.name;
              if (l != null && l !== "auto") {
                var i = e.get(l);
                if (i !== void 0) {
                  var o = ll(
                    n.default,
                    n.share
                  );
                  if (o !== "none" && (ui(
                    t,
                    l,
                    o,
                    null,
                    !1
                  ) ? (o = t.stateNode, i.paired = o, o.paired = i, hi(t, n.onShare)) : jn(t.child, !1)), e.delete(l), e.size === 0) break;
                }
              }
            }
            Ns(t);
          }
          t = t.sibling;
        }
    }
  }
  function Ds(t) {
    if (t.tag === 30) {
      var e = t.memoizedProps, n = nl(e, t.stateNode), l = Pe !== null ? Pe.get(n) : void 0, i = ll(
        e.default,
        l !== void 0 ? e.share : e.exit
      );
      i !== "none" && (ui(t, n, i, null, !1) ? l !== void 0 ? (i = t.stateNode, l.paired = i, i.paired = l, Pe.delete(n), hi(t, e.onShare)) : hi(t, e.onExit) : jn(t.child, !1)), Pe !== null && Ns(t);
    } else if ((t.subtreeFlags & 33554432) !== 0)
      for (t = t.child; t !== null; )
        Ds(t), t = t.sibling;
    else
      Pe !== null && Ns(t);
  }
  function Th(t) {
    for (t = t.child; t !== null; ) {
      if (t.tag === 30) {
        var e = t.memoizedProps, n = nl(e, t.stateNode);
        e = ll(e.default, e.update), t.flags &= -5, e !== "none" && ui(
          t,
          n,
          e,
          t.memoizedState = [],
          !1
        );
      } else
        (t.subtreeFlags & 33554432) !== 0 && Th(t);
      t = t.sibling;
    }
  }
  function zs(t) {
    if ((t.subtreeFlags & 18874368) !== 0)
      for (t = t.child; t !== null; ) {
        if (t.tag !== 22 || t.memoizedState === null) {
          if (t.tag === 30 && (t.flags & 18874368) !== 0) {
            var e = t.stateNode;
            e.paired !== null && (e.paired = null, jn(t.child, !1));
          }
          zs(t);
        }
        t = t.sibling;
      }
  }
  function Pu(t) {
    if (t.tag === 30)
      t.stateNode.paired = null, jn(t.child, !1), zs(t);
    else if ((t.subtreeFlags & 33554432) !== 0)
      for (t = t.child; t !== null; )
        Pu(t), t = t.sibling;
    else zs(t);
  }
  function wh(t) {
    for (t = t.child; t !== null; )
      t.tag === 30 ? jn(t.child, !1) : (t.subtreeFlags & 33554432) !== 0 && wh(t), t = t.sibling;
  }
  function Ms(t, e, n, l, i, o, s) {
    for (var h = !1; e !== null; ) {
      if (e.tag === 5) {
        var T = e.stateNode;
        if (o !== null && Ye < o.length) {
          var z = o[Ye], j = df(T);
          (z.view || j.view) && (h = !0);
          var G;
          if (G = (t.flags & 4) === 0)
            if (j.clip) G = !0;
            else {
              G = z.rect;
              var A = j.rect;
              G = G.y !== A.y || G.x !== A.x || G.height !== A.height || G.width !== A.width;
            }
          G && (t.flags |= 4), j.abs ? j = !z.abs : (z = z.rect, j = j.rect, j = z.height !== j.height || z.width !== j.width), j && (t.flags |= 32);
        } else t.flags |= 32;
        (t.flags & 4) !== 0 && Eg(
          T,
          Ye === 0 ? n : n + "_" + Ye,
          i
        ), h && (t.flags & 4) !== 0 || (Hn === null && (Hn = []), Hn.push(
          T,
          Ye === 0 ? l : l + "_" + Ye,
          e.memoizedProps
        )), Ye++;
      } else (e.tag !== 22 || e.memoizedState === null) && (e.tag === 30 && s ? t.flags |= e.flags & 32 : Ms(
        t,
        e.child,
        n,
        l,
        i,
        o,
        s
      ) && (h = !0));
      e = e.sibling;
    }
    return h;
  }
  function Ch(t, e) {
    for (t = t.child; t !== null; ) {
      if (t.tag === 30) {
        var n = t.memoizedProps, l = t.stateNode, i = nl(n, l), o = ll(n.default, n.update), s;
        s = t.memoizedState, t.memoizedState = null, l = t;
        var h = t.child;
        Ye = 0, i = Ms(
          l,
          h,
          i,
          i,
          o,
          s,
          !1
        ), (t.flags & 4) !== 0 && i && hi(t, n.onUpdate);
      } else
        (t.subtreeFlags & 33554432) !== 0 && Ch(t);
      t = t.sibling;
    }
  }
  var me = !1, Lt = !1, Bn = !1, Us = !1, Oh = typeof WeakSet == "function" ? WeakSet : Set, ve = null, Ln = !1, xo = !1, Wu = !1, Hs = !1;
  function A1(t, e, n) {
    if (t = t.containerInfo, uf = Ci, t = Nm(t), Ec(t)) {
      if ("selectionStart" in t)
        var l = {
          start: t.selectionStart,
          end: t.selectionEnd
        };
      else
        t: {
          l = (l = t.ownerDocument) && l.defaultView || window;
          var i = l.getSelection && l.getSelection();
          if (i && i.rangeCount !== 0) {
            l = i.anchorNode;
            var o = i.anchorOffset, s = i.focusNode;
            i = i.focusOffset;
            try {
              l.nodeType, s.nodeType;
            } catch {
              l = null;
              break t;
            }
            var h = 0, T = -1, z = -1, j = 0, G = 0, A = t, U = null;
            e: for (; ; ) {
              for (var nt; A !== l || o !== 0 && A.nodeType !== 3 || (T = h + o), A !== s || i !== 0 && A.nodeType !== 3 || (z = h + i), A.nodeType === 3 && (h += A.nodeValue.length), (nt = A.firstChild) !== null; )
                U = A, A = nt;
              for (; ; ) {
                if (A === t) break e;
                if (U === l && ++j === o && (T = h), U === s && ++G === i && (z = h), (nt = A.nextSibling) !== null) break;
                A = U, U = A.parentNode;
              }
              A = nt;
            }
            l = T === -1 || z === -1 ? null : { start: T, end: z };
          } else l = null;
        }
      l = l || { start: 0, end: 0 };
    } else l = null;
    for (rf = { focusedElem: t, selectionRange: l }, Ci = !1, n = (n & 335544064) === n, ve = e, e = n ? 9270 : 1024; ve !== null; ) {
      if (t = ve, n && (l = t.deletions, l !== null))
        for (o = 0; o < l.length; o++)
          n && Ds(l[o]);
      if (t.alternate === null && (t.flags & 2) !== 0)
        n && Sh(t), tr(n);
      else {
        if (t.tag === 22) {
          if (l = t.alternate, t.memoizedState !== null) {
            l !== null && l.memoizedState === null && n && Ds(l), tr(n);
            continue;
          } else if (l !== null && l.memoizedState !== null) {
            n && Sh(t), tr(n);
            continue;
          }
        }
        l = t.child, (t.subtreeFlags & e) !== 0 && l !== null ? (l.return = t, ve = l) : (n && Th(t), tr(n));
      }
    }
    Pe = null;
  }
  function tr(t) {
    for (; ve !== null; ) {
      var e = ve, n = t, l = e.alternate, i = e.flags;
      switch (e.tag) {
        case 0:
        case 11:
        case 15:
          break;
        case 1:
          if ((i & 1024) !== 0 && l !== null) {
            n = void 0, i = l.memoizedProps, l = l.memoizedState;
            var o = e.stateNode;
            try {
              var s = Ea(
                e.type,
                i
              );
              n = o.getSnapshotBeforeUpdate(
                s,
                l
              ), o.__reactInternalSnapshotBeforeUpdate = n;
            } catch (h) {
              qt(e, e.return, h);
            }
          }
          break;
        case 3:
          if ((i & 1024) !== 0) {
            if (l = e.stateNode.containerInfo, n = l.nodeType, n === 9)
              hf(l);
            else if (n === 1)
              switch (l.nodeName) {
                case "HEAD":
                case "HTML":
                case "BODY":
                  hf(l);
                  break;
                default:
                  l.textContent = "";
              }
          }
          break;
        case 5:
        case 26:
        case 27:
        case 6:
        case 4:
        case 17:
          break;
        case 30:
          n && l !== null && (n = nl(
            l.memoizedProps,
            l.stateNode
          ), i = e.memoizedProps, i = ll(i.default, i.update), i !== "none" && ui(
            l,
            n,
            i,
            l.memoizedState = [],
            !0
          ));
          break;
        default:
          if ((i & 1024) !== 0) throw Error(c(163));
      }
      if (l = e.sibling, l !== null) {
        l.return = e.return, ve = l;
        break;
      }
      ve = e.return;
    }
  }
  function _h(t, e, n) {
    var l = n.flags;
    switch (n.tag) {
      case 0:
      case 11:
      case 15:
        Yn(t, n), l & 4 && So(5, n);
        break;
      case 1:
        if (Yn(t, n), l & 4)
          if (t = n.stateNode, e === null)
            try {
              t.componentDidMount();
            } catch (s) {
              qt(n, n.return, s);
            }
          else {
            var i = Ea(
              n.type,
              e.memoizedProps
            );
            e = e.memoizedState;
            try {
              t.componentDidUpdate(
                i,
                e,
                t.__reactInternalSnapshotBeforeUpdate
              );
            } catch (s) {
              qt(
                n,
                n.return,
                s
              );
            }
          }
        l & 64 && hh(n), l & 512 && Un(n, n.return);
        break;
      case 3:
        if (Yn(t, n), l & 64 && (t = n.updateQueue, t !== null)) {
          if (e = null, n.child !== null)
            switch (n.child.tag) {
              case 27:
              case 5:
                e = n.child.stateNode;
                break;
              case 1:
                e = n.child.stateNode;
            }
          try {
            av(t, e);
          } catch (s) {
            qt(n, n.return, s);
          }
        }
        break;
      case 27:
        e === null && l & 4 && bh(n);
      case 26:
      case 5:
        Yn(t, n), e === null && l & 4 && Cs(n), l & 512 && Un(n, n.return);
        break;
      case 12:
        Yn(t, n);
        break;
      case 31:
        Yn(t, n), l & 4 && Dh(t, n);
        break;
      case 13:
        Yn(t, n), l & 4 && zh(t, n), l & 64 && (t = n.memoizedState, t !== null && (t = t.dehydrated, t !== null && (n = q1.bind(
          null,
          n
        ), ES(t, n))));
        break;
      case 22:
        if (l = n.memoizedState !== null || me, !l) {
          var o = e !== null && e.memoizedState !== null || Lt;
          e = me, i = Lt, me = l, (Lt = o) && !i ? (l = 2, (n.subtreeFlags & 8772) !== 0 && (l |= 1), Cn(
            t,
            n,
            l
          )) : Yn(t, n), me = e, Lt = i;
        }
        break;
      case 30:
        Yn(t, n), l & 512 && Un(n, n.return);
        break;
      case 7:
        l & 512 && Un(n, n.return);
      default:
        Yn(t, n);
    }
  }
  function js(t, e) {
    for (t = t.child; t !== null; )
      Ah(t, e), t = t.sibling;
  }
  function Ah(t, e) {
    switch (t.tag) {
      case 5:
      case 26:
        try {
          var n = t.stateNode;
          if (e) {
            var l = n.style;
            typeof l.setProperty == "function" ? l.setProperty("display", "none", "important") : l.display = "none";
          } else {
            var i = t.stateNode, o = t.memoizedProps.style, s = o != null && o.hasOwnProperty("display") ? o.display : null;
            i.style.display = s == null || typeof s == "boolean" ? "" : ("" + s).trim();
          }
        } catch (T) {
          qt(t, t.return, T);
        }
        Bs(t, e);
        break;
      case 6:
        try {
          t.stateNode.nodeValue = e ? "" : t.memoizedProps, Mt = !0;
        } catch (T) {
          qt(t, t.return, T);
        }
        break;
      case 18:
        try {
          var h = t.stateNode;
          e ? Sg(h, !0) : Sg(t.stateNode, !1);
        } catch (T) {
          qt(t, t.return, T);
        }
        break;
      case 22:
      case 23:
        t.memoizedState === null && js(t, e);
        break;
      default:
        js(t, e);
    }
  }
  function Bs(t, e) {
    if (t.subtreeFlags & 67108864)
      for (t = t.child; t !== null; ) {
        t: {
          var n = t, l = e;
          switch (n.tag) {
            case 4:
              Ah(n, l);
              break t;
            case 22:
              n.memoizedState === null && Bs(n, l);
              break t;
            default:
              Bs(n, l);
          }
        }
        t = t.sibling;
      }
  }
  function Rh(t) {
    var e = t.alternate;
    e !== null && (t.alternate = null, Rh(e)), t.child = null, t.deletions = null, t.sibling = null, t.tag === 5 && (e = t.stateNode, e !== null && iu(e)), t.stateNode = null, t.return = null, t.dependencies = null, t.memoizedProps = null, t.memoizedState = null, t.pendingProps = null, t.stateNode = null, t.updateQueue = null;
  }
  var Ft = null, qe = !1;
  function Tn(t, e, n) {
    for (n = n.child; n !== null; )
      Nh(t, e, n), n = n.sibling;
  }
  function Nh(t, e, n) {
    if (Gt && typeof Gt.onCommitFiberUnmount == "function")
      try {
        Gt.onCommitFiberUnmount(Wt, n);
      } catch {
      }
    switch (n.tag) {
      case 26:
        Lt || xe(n, e), Tn(
          t,
          e,
          n
        ), n.memoizedState ? n.memoizedState.count-- : n.stateNode && !Lt && (n = n.stateNode, n.parentNode.removeChild(n));
        break;
      case 27:
        Lt || xe(n, e), Eo(n);
        var l = Ft, i = qe;
        Xl(n.type) && (Ft = n.stateNode, qe = !1), Tn(
          t,
          e,
          n
        ), Ug(
          n.stateNode,
          n.type,
          n.memoizedProps
        ), Ft = l, qe = i;
        break;
      case 5:
        Lt || xe(n, e), Eo(n);
      case 6:
        if (n.tag === 6 && Eo(n), l = Ft, i = qe, Ft = null, Tn(
          t,
          e,
          n
        ), Ft = l, qe = i, Ft !== null)
          if (qe)
            try {
              (Ft.nodeType === 9 ? Ft.body : Ft.nodeName === "HTML" ? Ft.ownerDocument.body : Ft).removeChild(n.stateNode), Mt = !0;
            } catch (o) {
              qt(
                n,
                e,
                o
              );
            }
          else
            try {
              Ft.removeChild(n.stateNode), Mt = !0;
            } catch (o) {
              qt(
                n,
                e,
                o
              );
            }
        break;
      case 18:
        Ft !== null && (qe ? (t = Ft, bg(
          t.nodeType === 9 ? t.body : t.nodeName === "HTML" ? t.ownerDocument.body : t,
          n.stateNode
        ), Oi(t)) : bg(Ft, n.stateNode));
        break;
      case 4:
        l = Ft, i = qe, Ft = n.stateNode.containerInfo, qe = !0, Tn(
          t,
          e,
          n
        ), Ft = l, qe = i;
        break;
      case 0:
      case 11:
      case 14:
      case 15:
        jl(2, n, e), Lt || jl(4, n, e), Tn(
          t,
          e,
          n
        );
        break;
      case 1:
        Lt || (xe(n, e), l = n.stateNode, typeof l.componentWillUnmount == "function" && gh(
          n,
          e,
          l
        )), Tn(
          t,
          e,
          n
        );
        break;
      case 21:
        Tn(
          t,
          e,
          n
        );
        break;
      case 22:
        Lt = (l = Lt) || n.memoizedState !== null, Tn(
          t,
          e,
          n
        ), Lt = l;
        break;
      case 30:
        xe(n, e), Tn(
          t,
          e,
          n
        );
        break;
      case 7:
        Lt || xe(n, e), Tn(
          t,
          e,
          n
        );
        break;
      default:
        Tn(
          t,
          e,
          n
        );
    }
  }
  function Dh(t, e) {
    if (e.memoizedState === null && (t = e.alternate, t !== null && (t = t.memoizedState, t !== null))) {
      t = t.dehydrated;
      try {
        Oi(t);
      } catch (n) {
        qt(e, e.return, n);
      }
    }
  }
  function zh(t, e) {
    if (e.memoizedState === null && (t = e.alternate, t !== null && (t = t.memoizedState, t !== null && (t = t.dehydrated, t !== null))))
      try {
        Oi(t);
      } catch (n) {
        qt(e, e.return, n);
      }
  }
  function R1(t) {
    switch (t.tag) {
      case 31:
      case 13:
      case 19:
        var e = t.stateNode;
        return e === null && (e = t.stateNode = new Oh()), e;
      case 22:
        return t = t.stateNode, e = t._retryCache, e === null && (e = t._retryCache = new Oh()), e;
      default:
        throw Error(c(435, t.tag));
    }
  }
  function er(t, e) {
    var n = R1(t);
    e.forEach(function(l) {
      if (!n.has(l)) {
        n.add(l);
        var i = V1.bind(null, t, l);
        l.then(i, i);
      }
    });
  }
  function ze(t, e, n) {
    var l = e.deletions;
    if (l !== null)
      for (var i = 0; i < l.length; i++) {
        var o = l[i], s = t, h = e, T = h;
        t: for (; T !== null; ) {
          switch (T.tag) {
            case 27:
              if (Xl(T.type)) {
                Ft = T.stateNode, qe = !1;
                break t;
              }
              break;
            case 5:
              Ft = T.stateNode, qe = !1;
              break t;
            case 3:
            case 4:
              Ft = T.stateNode.containerInfo, qe = !0;
              break t;
          }
          T = T.return;
        }
        if (Ft === null) throw Error(c(160));
        Nh(s, h, o), Ft = null, qe = !1, s = o.alternate, s !== null && (s.return = null), o.return = null;
      }
    if (e.subtreeFlags & 13886)
      for (e = e.child; e !== null; )
        Mh(e, t, n), e = e.sibling;
  }
  var wn = null;
  function Mh(t, e, n) {
    var l = t.alternate, i = t.flags;
    switch (t.tag) {
      case 0:
      case 11:
      case 14:
      case 15:
        if (i & 4 && (l = t.updateQueue, l = l !== null ? l.events : null, l !== null))
          for (var o = 0; o < l.length; o++) {
            var s = l[o];
            s.ref.impl = s.nextImpl;
          }
        ze(e, t, n), Me(t), i & 4 && (jl(3, t, t.return), So(3, t), jl(5, t, t.return));
        break;
      case 1:
        ze(e, t, n), Me(t), i & 512 && (Lt || l === null || xe(l, l.return)), i & 64 && me && (t = t.updateQueue, t !== null && (e = t.callbacks, e !== null && (n = t.shared.hiddenCallbacks, t.shared.hiddenCallbacks = n === null ? e : n.concat(e))));
        break;
      case 26:
        if (o = wn, ze(e, t, n), Me(t), i & 512 && (Lt || l === null || xe(l, l.return)), i & 4)
          if (i = l !== null ? l.memoizedState : null, n = t.memoizedState, l === null)
            if (n === null)
              if (t.stateNode === null)
                if (me)
                  t.stateNode = gg(
                    t.type,
                    t.memoizedProps,
                    e.containerInfo,
                    t
                  );
                else {
                  t: {
                    e = t.type, n = t.memoizedProps, i = o.ownerDocument || o;
                    e: switch (e) {
                      case "title":
                        l = i.getElementsByTagName("title")[0], (!l || l[Ki] || l[pe] || l.namespaceURI === "http://www.w3.org/2000/svg" || l.hasAttribute("itemprop")) && (l = i.createElement(e), i.head.insertBefore(
                          l,
                          i.querySelector("head > title")
                        )), Te(l, e, n), l[pe] = t, fe(l), e = l;
                        break t;
                      case "link":
                        if (o = qg(
                          "link",
                          "href",
                          i
                        ).get(e + (n.href || ""))) {
                          for (s = 0; s < o.length; s++)
                            if (l = o[s], l.getAttribute("href") === (n.href == null || n.href === "" ? null : n.href) && l.getAttribute("rel") === (n.rel == null ? null : n.rel) && l.getAttribute("title") === (n.title == null ? null : n.title) && l.getAttribute("crossorigin") === (n.crossOrigin == null ? null : n.crossOrigin)) {
                              o.splice(s, 1);
                              break e;
                            }
                        }
                        l = i.createElement(e), Te(l, e, n), i.head.appendChild(l);
                        break;
                      case "meta":
                        if (o = qg(
                          "meta",
                          "content",
                          i
                        ).get(e + (n.content || ""))) {
                          for (s = 0; s < o.length; s++)
                            if (l = o[s], l.getAttribute("content") === (n.content == null ? null : "" + n.content) && l.getAttribute("name") === (n.name == null ? null : n.name) && l.getAttribute("property") === (n.property == null ? null : n.property) && l.getAttribute("http-equiv") === (n.httpEquiv == null ? null : n.httpEquiv) && l.getAttribute("charset") === (n.charSet == null ? null : n.charSet)) {
                              o.splice(s, 1);
                              break e;
                            }
                        }
                        l = i.createElement(e), Te(l, e, n), i.head.appendChild(l);
                        break;
                      default:
                        throw Error(c(468, e));
                    }
                    l[pe] = t, fe(l), e = l;
                  }
                  t.stateNode = e;
                }
              else
                me || xf(o, t.type, t.stateNode);
            else
              t.stateNode = Yg(
                o,
                n,
                t.memoizedProps
              );
          else
            i !== n ? (i === null ? (e = l.stateNode, e === null || Lt || e.parentNode.removeChild(e)) : i.count--, n === null ? me || xf(o, t.type, t.stateNode) : Yg(o, n, t.memoizedProps)) : n === null && t.stateNode !== null && Os(
              t,
              t.memoizedProps,
              l.memoizedProps
            );
        break;
      case 27:
        ze(e, t, n), Me(t), i & 512 && (Lt || l === null || xe(l, l.return)), l !== null && i & 4 && Os(
          t,
          t.memoizedProps,
          l.memoizedProps
        );
        break;
      case 5:
        if (o = Bn, Bn = !1, ze(e, t, n), Bn = o, Me(t), i & 512 && (Lt || l === null || xe(l, l.return)), t.flags & 32) {
          e = t.stateNode;
          try {
            Xa(e, ""), Mt = !0;
          } catch (j) {
            qt(t, t.return, j);
          }
        }
        i & 4 && t.stateNode != null && (e = t.memoizedProps, Os(
          t,
          e,
          l !== null ? l.memoizedProps : e
        )), i & 1024 && (Us = !0);
        break;
      case 6:
        if (ze(e, t, n), Me(t), i & 4) {
          if (t.stateNode === null)
            throw Error(c(162));
          e = t.memoizedProps, n = t.stateNode;
          try {
            n.nodeValue = e, Mt = !0;
          } catch (j) {
            qt(t, t.return, j);
          }
        }
        break;
      case 3:
        if (Mt = !1, gr = null, o = wn, wn = Do(e.containerInfo), ze(e, t, n), wn = o, Me(t), i & 4 && l !== null && l.memoizedState.isDehydrated)
          try {
            Oi(e.containerInfo);
          } catch (j) {
            qt(t, t.return, j);
          }
        Us && (Us = !1, Uh(t)), Mt = !1;
        break;
      case 4:
        i = Bn, Bn = me, l = tm(), o = wn, wn = Do(
          t.stateNode.containerInfo
        ), ze(e, t, n), Me(t), wn = o, Mt && xo && (Wu = !0), Mt = l, Bn = i;
        break;
      case 12:
        ze(e, t, n), Me(t);
        break;
      case 31:
        ze(e, t, n), Me(t), i & 4 && (e = t.updateQueue, e !== null && (t.updateQueue = null, er(t, e)));
        break;
      case 13:
        ze(e, t, n), Me(t), t.child.flags & 8192 && t.memoizedState !== null != (l !== null && l.memoizedState !== null) && (ar = Ae()), i & 4 && (e = t.updateQueue, e !== null && (t.updateQueue = null, er(t, e)));
        break;
      case 22:
        o = t.memoizedState !== null, s = l !== null && l.memoizedState !== null;
        var h = me, T = Lt, z = Bn;
        me = h || o, Bn = z || o, Lt = T || s, ze(e, t, n), Lt = T, Bn = z, me = h, Me(t), i & 8192 && (e = t.stateNode, e._visibility = o ? e._visibility & -2 : e._visibility | 1, !o || l === null || s || me || Lt || (e = s || Lt, n = me, l = Lt, me = o || me, Lt = e, Bl(t, 2), me = n, Lt = l), !o && Bn || js(t, o)), i & 4 && (e = t.updateQueue, e !== null && (n = e.retryQueue, n !== null && (e.retryQueue = null, er(t, n))));
        break;
      case 19:
        ze(e, t, n), Me(t), i & 4 && (e = t.updateQueue, e !== null && (t.updateQueue = null, er(t, e)));
        break;
      case 30:
        i & 512 && (Lt || l === null || xe(l, l.return)), i = tm(), o = xo, s = (n & 335544064) === n, h = t.memoizedProps, xo = s && ll(
          h.default,
          h.update
        ) !== "none", ze(e, t, n), Me(t), s && l !== null && Mt && (t.flags |= 4), xo = o, Mt = i;
        break;
      case 21:
        break;
      case 7:
        i & 512 && (Lt || l === null || xe(l, l.return)), l && l.stateNode !== null && (l.stateNode._fragmentFiber = t);
      default:
        ze(e, t, n), Me(t);
    }
  }
  function Me(t) {
    var e = t.flags;
    if (e & 2) {
      try {
        for (var n, l = t.return; l !== null; ) {
          if (ph(l)) {
            n = l;
            break;
          }
          l = l.return;
        }
        l = null;
        for (var i = t.return; i !== null; ) {
          if (ws(i)) {
            var o = i.stateNode;
            l === null ? l = [o] : l.push(o);
          }
          if (Ts(i)) break;
          i = i.return;
        }
        var s = l;
        if (n == null) throw Error(c(160));
        switch (n.tag) {
          case 27:
            var h = n.stateNode, T = _s(t);
            Fu(
              t,
              T,
              h,
              s
            );
            break;
          case 5:
            var z = n.stateNode;
            n.flags & 32 && (Xa(z, ""), n.flags &= -33);
            var j = _s(t);
            Fu(
              t,
              j,
              z,
              s
            );
            break;
          case 3:
          case 4:
            var G = n.stateNode.containerInfo, A = _s(t);
            As(
              t,
              A,
              G,
              s
            );
            break;
          default:
            throw Error(c(161));
        }
      } catch (U) {
        qt(t, t.return, U);
      }
      t.flags &= -3;
    }
    e & 4096 && (t.flags &= -4097);
  }
  function Uh(t) {
    if (t.subtreeFlags & 1024)
      for (t = t.child; t !== null; ) {
        var e = t;
        Uh(e), e.tag === 5 && e.flags & 1024 && (e = e.stateNode, Ci = !0, e.reset(), Ci = !1), t = t.sibling;
      }
  }
  function ri(t, e) {
    if (e.subtreeFlags & 9270)
      for (e = e.child; e !== null; )
        Hh(e, t), e = e.sibling;
    else Ch(e);
  }
  function Hh(t, e) {
    var n = t.alternate;
    if (n === null) Rs(t, !1);
    else
      switch (t.tag) {
        case 3:
          if (Hs = Ln = !1, Eh(), ri(e, t), !Ln && !Wu) {
            if (t = Hn, t !== null)
              for (var l = 0; l < t.length; l += 3) {
                n = t[l];
                var i = t[l + 1];
                xg(n, t[l + 2]), n = n.ownerDocument.documentElement, n !== null && n.animate(
                  { opacity: [0, 0], pointerEvents: ["none", "none"] },
                  {
                    duration: 0,
                    fill: "forwards",
                    pseudoElement: "::view-transition-group(" + i + ")"
                  }
                );
              }
            t = e.containerInfo, t = t.nodeType === 9 ? t.documentElement : t.ownerDocument.documentElement, t !== null && t.style.viewTransitionName === "" && (t.style.viewTransitionName = "none", t.animate(
              { opacity: [0, 0], pointerEvents: ["none", "none"] },
              {
                duration: 0,
                fill: "forwards",
                pseudoElement: "::view-transition-group(root)"
              }
            ), t.animate(
              { width: [0, 0], height: [0, 0] },
              {
                duration: 0,
                fill: "forwards",
                pseudoElement: "::view-transition"
              }
            )), Hs = !0;
          }
          Hn = null;
          break;
        case 5:
          ri(e, t);
          break;
        case 4:
          l = Ln, Ln = !1, ri(e, t), Ln && (Wu = !0), Ln = l;
          break;
        case 22:
          t.memoizedState === null && (n.memoizedState !== null ? Rs(t, !1) : ri(e, t));
          break;
        case 30:
          l = Ln, i = Eh(), Ln = !1, ri(e, t), Ln && (t.flags |= 4);
          var o = t.memoizedProps, s = t.stateNode;
          e = nl(o, s), s = nl(n.memoizedProps, s);
          var h = ll(o.default, o.update);
          h === "none" ? e = !1 : (o = n.memoizedState, n.memoizedState = null, n = t.child, Ye = 0, e = Ms(
            t,
            n,
            e,
            s,
            h,
            o,
            !0
          ), Ye !== (o === null ? 0 : o.length) && (t.flags |= 32)), (t.flags & 4) !== 0 && e ? (hi(
            t,
            t.memoizedProps.onUpdate
          ), Hn = i) : i !== null && (i.push.apply(i, Hn), Hn = i), Ln = (t.flags & 32) !== 0 ? !0 : l;
          break;
        default:
          ri(e, t);
      }
  }
  function Yn(t, e) {
    if (e.subtreeFlags & 8772)
      for (e = e.child; e !== null; )
        _h(t, e.alternate, e), e = e.sibling;
  }
  function Bl(t, e) {
    for (t = t.child; t !== null; ) {
      var n = t, l = e;
      switch (n.tag) {
        case 0:
        case 11:
        case 14:
        case 15:
          jl(4, n, n.return), Bl(
            n,
            l
          );
          break;
        case 1:
          xe(n, n.return);
          var i = n.stateNode;
          typeof i.componentWillUnmount == "function" && gh(
            n,
            n.return,
            i
          ), Bl(
            n,
            l
          );
          break;
        case 27:
          (l & 2) !== 0 && Ug(
            n.stateNode,
            n.type,
            n.memoizedProps
          );
        case 5:
          xe(n, n.return), n.tag !== 5 && n.tag !== 27 || Eo(n), Bl(
            n,
            l
          );
          break;
        case 6:
          Eo(n);
          break;
        case 26:
          xe(n, n.return), i = n.stateNode, n.memoizedState !== null || i === null || Lt || i.parentNode.removeChild(i), Bl(
            n,
            l
          );
          break;
        case 22:
          n.memoizedState === null && Bl(
            n,
            l
          );
          break;
        case 30:
          xe(n, n.return), Bl(
            n,
            l
          );
          break;
        case 7:
          xe(n, n.return);
        default:
          Bl(
            n,
            l
          );
      }
      t = t.sibling;
    }
  }
  function Cn(t, e, n) {
    for (n = (e.subtreeFlags & 8772) !== 0 ? n : n & -2, e = e.child; e !== null; ) {
      var l = e.alternate, i = t, o = e, s = o.flags, h = (n & 1) !== 0;
      switch (o.tag) {
        case 0:
        case 11:
        case 15:
          Cn(
            i,
            o,
            n
          ), So(4, o);
          break;
        case 1:
          if (Cn(
            i,
            o,
            n
          ), l = o, i = l.stateNode, typeof i.componentDidMount == "function")
            try {
              i.componentDidMount();
            } catch (j) {
              qt(l, l.return, j);
            }
          if (l = o, i = l.updateQueue, i !== null) {
            var T = l.stateNode;
            try {
              var z = i.shared.hiddenCallbacks;
              if (z !== null)
                for (i.shared.hiddenCallbacks = null, i = 0; i < z.length; i++)
                  lv(z[i], T);
            } catch (j) {
              qt(l, l.return, j);
            }
          }
          h && s & 64 && hh(o), Un(o, o.return);
          break;
        case 27:
          (n & 2) !== 0 && bh(o);
        case 5:
          o.tag !== 5 && o.tag !== 27 || yh(o), Cn(
            i,
            o,
            n
          ), h && l === null && s & 4 && Cs(o), Un(o, o.return);
          break;
        case 6:
          yh(o);
          break;
        case 26:
          T = o.stateNode, o.memoizedState !== null || T === null || me || xf(
            Do(T.ownerDocument),
            o.type,
            T
          ), Cn(
            i,
            o,
            n
          ), h && l === null && s & 4 && Cs(o), Un(o, o.return);
          break;
        case 12:
          Cn(
            i,
            o,
            n
          );
          break;
        case 31:
          Cn(
            i,
            o,
            n
          ), h && s & 4 && Dh(i, o);
          break;
        case 13:
          Cn(
            i,
            o,
            n
          ), h && s & 4 && zh(i, o);
          break;
        case 22:
          o.memoizedState === null && Cn(
            i,
            o,
            n
          ), Un(o, o.return);
          break;
        case 30:
          Cn(
            i,
            o,
            n
          ), Un(o, o.return);
          break;
        case 7:
          Un(o, o.return);
        default:
          Cn(
            i,
            o,
            n
          );
      }
      e = e.sibling;
    }
  }
  function Ls(t, e) {
    var n = null;
    t !== null && t.memoizedState !== null && t.memoizedState.cachePool !== null && (n = t.memoizedState.cachePool.pool), t = null, e.memoizedState !== null && e.memoizedState.cachePool !== null && (t = e.memoizedState.cachePool.pool), t !== n && (t != null && t.refCount++, n != null && oo(n));
  }
  function Ys(t, e) {
    t = null, e.alternate !== null && (t = e.alternate.memoizedState.cache), e = e.memoizedState.cache, e !== t && (e.refCount++, t != null && oo(t));
  }
  function vn(t, e, n, l) {
    var i = (n & 335544064) === n;
    if (e.subtreeFlags & (i ? 10262 : 10256))
      for (e = e.child; e !== null; )
        jh(
          t,
          e,
          n,
          l
        ), e = e.sibling;
    else i && wh(e);
  }
  function jh(t, e, n, l) {
    var i = (n & 335544064) === n;
    i && e.alternate === null && e.return !== null && e.return.alternate !== null && Pu(e);
    var o = e.flags;
    switch (e.tag) {
      case 0:
      case 11:
      case 15:
        vn(
          t,
          e,
          n,
          l
        ), o & 2048 && So(9, e);
        break;
      case 1:
        vn(
          t,
          e,
          n,
          l
        );
        break;
      case 3:
        vn(
          t,
          e,
          n,
          l
        ), i && Hs && (t = t.containerInfo, t = t.nodeType === 9 ? t.body : t.nodeName === "HTML" ? t.ownerDocument.body : t, t.style.viewTransitionName === "root" && (t.style.viewTransitionName = ""), t = t.ownerDocument.documentElement, t !== null && t.style.viewTransitionName === "none" && (t.style.viewTransitionName = "")), o & 2048 && (o = null, e.alternate !== null && (o = e.alternate.memoizedState.cache), e = e.memoizedState.cache, e !== o && (e.refCount++, o != null && oo(o)));
        break;
      case 12:
        if (o & 2048) {
          vn(
            t,
            e,
            n,
            l
          ), o = e.stateNode;
          try {
            var s = e.memoizedProps, h = s.id, T = s.onPostCommit;
            typeof T == "function" && T(
              h,
              e.alternate === null ? "mount" : "update",
              o.passiveEffectDuration,
              -0
            );
          } catch (z) {
            qt(e, e.return, z);
          }
        } else
          vn(
            t,
            e,
            n,
            l
          );
        break;
      case 31:
        vn(
          t,
          e,
          n,
          l
        );
        break;
      case 13:
        vn(
          t,
          e,
          n,
          l
        );
        break;
      case 23:
        break;
      case 22:
        s = e.stateNode, h = e.alternate, e.memoizedState !== null ? (i && h !== null && h.memoizedState === null && Pu(h), s._visibility & 2 ? vn(
          t,
          e,
          n,
          l
        ) : To(
          t,
          e
        )) : (i && h !== null && h.memoizedState !== null && Pu(e), s._visibility & 2 ? vn(
          t,
          e,
          n,
          l
        ) : (s._visibility |= 2, ci(
          t,
          e,
          n,
          l,
          (e.subtreeFlags & 10256) !== 0 || !1
        ))), o & 2048 && Ls(h, e);
        break;
      case 24:
        vn(
          t,
          e,
          n,
          l
        ), o & 2048 && Ys(e.alternate, e);
        break;
      case 30:
        i && (o = e.alternate, o !== null && (jn(o.child, !0), jn(e.child, !0))), vn(
          t,
          e,
          n,
          l
        );
        break;
      default:
        vn(
          t,
          e,
          n,
          l
        );
    }
  }
  function ci(t, e, n, l, i) {
    for (i = i && ((e.subtreeFlags & 10256) !== 0 || !1), e = e.child; e !== null; ) {
      var o = t, s = e, h = n, T = l, z = s.flags;
      switch (s.tag) {
        case 0:
        case 11:
        case 15:
          ci(
            o,
            s,
            h,
            T,
            i
          ), So(8, s);
          break;
        case 23:
          break;
        case 22:
          var j = s.stateNode;
          s.memoizedState !== null ? j._visibility & 2 ? ci(
            o,
            s,
            h,
            T,
            i
          ) : To(
            o,
            s
          ) : (j._visibility |= 2, ci(
            o,
            s,
            h,
            T,
            i
          )), i && z & 2048 && Ls(
            s.alternate,
            s
          );
          break;
        case 24:
          ci(
            o,
            s,
            h,
            T,
            i
          ), i && z & 2048 && Ys(s.alternate, s);
          break;
        default:
          ci(
            o,
            s,
            h,
            T,
            i
          );
      }
      e = e.sibling;
    }
  }
  function To(t, e) {
    if (e.subtreeFlags & 10256)
      for (e = e.child; e !== null; ) {
        var n = t, l = e, i = l.flags;
        switch (l.tag) {
          case 22:
            To(n, l), i & 2048 && Ls(
              l.alternate,
              l
            );
            break;
          case 24:
            To(n, l), i & 2048 && Ys(l.alternate, l);
            break;
          default:
            To(n, l);
        }
        e = e.sibling;
      }
  }
  var xa = 8192;
  function Ta(t, e, n) {
    if (t.subtreeFlags & xa)
      for (t = t.child; t !== null; )
        Bh(
          t,
          e,
          n
        ), t = t.sibling;
  }
  function Bh(t, e, n) {
    switch (t.tag) {
      case 26:
        Ta(
          t,
          e,
          n
        ), t.flags & xa && (t.memoizedState !== null ? HS(
          n,
          wn,
          t.memoizedState,
          t.memoizedProps
        ) : (t = t.stateNode, (e & 335544128) === e && kg(n, t)));
        break;
      case 5:
        Ta(
          t,
          e,
          n
        ), t.flags & xa && (t = t.stateNode, (e & 335544128) === e && kg(n, t));
        break;
      case 3:
      case 4:
        var l = wn;
        wn = Do(t.stateNode.containerInfo), Ta(
          t,
          e,
          n
        ), wn = l;
        break;
      case 22:
        t.memoizedState === null && (l = t.alternate, l !== null && l.memoizedState !== null ? (l = xa, xa = 16777216, Ta(
          t,
          e,
          n
        ), xa = l) : Ta(
          t,
          e,
          n
        ));
        break;
      case 30:
        if ((t.flags & xa) !== 0 && (l = t.memoizedProps.name, l != null && l !== "auto")) {
          var i = t.stateNode;
          i.paired = null, Pe === null && (Pe = /* @__PURE__ */ new Map()), Pe.set(l, i);
        }
        Ta(
          t,
          e,
          n
        );
        break;
      default:
        Ta(
          t,
          e,
          n
        );
    }
  }
  function Lh(t) {
    var e = t.alternate;
    if (e !== null && (t = e.child, t !== null)) {
      e.child = null;
      do
        e = t.sibling, t.sibling = null, t = e;
      while (t !== null);
    }
  }
  function wo(t) {
    var e = t.deletions;
    if ((t.flags & 16) !== 0) {
      if (e !== null)
        for (var n = 0; n < e.length; n++) {
          var l = e[n];
          ve = l, qh(
            l,
            t
          );
        }
      Lh(t);
    }
    if (t.subtreeFlags & 10256)
      for (t = t.child; t !== null; )
        Yh(t), t = t.sibling;
  }
  function Yh(t) {
    switch (t.tag) {
      case 0:
      case 11:
      case 15:
        wo(t), t.flags & 2048 && jl(9, t, t.return);
        break;
      case 3:
        wo(t);
        break;
      case 12:
        wo(t);
        break;
      case 22:
        var e = t.stateNode;
        t.memoizedState !== null && e._visibility & 2 && (t.return === null || t.return.tag !== 13) ? (e._visibility &= -3, nr(t)) : wo(t);
        break;
      default:
        wo(t);
    }
  }
  function nr(t) {
    var e = t.deletions;
    if ((t.flags & 16) !== 0) {
      if (e !== null)
        for (var n = 0; n < e.length; n++) {
          var l = e[n];
          ve = l, qh(
            l,
            t
          );
        }
      Lh(t);
    }
    for (t = t.child; t !== null; ) {
      switch (e = t, e.tag) {
        case 0:
        case 11:
        case 15:
          jl(8, e, e.return), nr(e);
          break;
        case 22:
          n = e.stateNode, n._visibility & 2 && (n._visibility &= -3, nr(e));
          break;
        default:
          nr(e);
      }
      t = t.sibling;
    }
  }
  function qh(t, e) {
    for (; ve !== null; ) {
      var n = ve;
      switch (n.tag) {
        case 0:
        case 11:
        case 15:
          jl(8, n, e);
          break;
        case 23:
        case 22:
          if (n.memoizedState !== null && n.memoizedState.cachePool !== null) {
            var l = n.memoizedState.cachePool.pool;
            l != null && l.refCount++;
          }
          break;
        case 24:
          oo(n.memoizedState.cache);
      }
      if (l = n.child, l !== null) l.return = n, ve = l;
      else
        t: for (n = t; ve !== null; ) {
          l = ve;
          var i = l.sibling, o = l.return;
          if (Rh(l), l === n) {
            ve = null;
            break t;
          }
          if (i !== null) {
            i.return = o, ve = i;
            break t;
          }
          ve = o;
        }
    }
  }
  var N1 = {
    getCacheForType: function(t) {
      var e = be(ae), n = e.data.get(t);
      return n === void 0 && (n = t(), e.data.set(t, n)), n;
    },
    cacheSignal: function() {
      return be(ae).controller.signal;
    }
  }, D1 = typeof WeakMap == "function" ? WeakMap : Map, jt = 0, kt = null, At = null, Nt = 0, Yt = 0, We = null, Ll = !1, si = !1, qs = !1, dl = 0, ee = 0, Yl = 0, wa = 0, lr = 0, tn = 0, fi = 0, Co = null, Ve = null, Vs = !1, ar = 0, Vh = 0, ir = 1 / 0, or = null, ql = null, $t = 0, On = null, Ca = null, qn = 0, Gs = 0, Xs = null, Gh = null, di = null, mi = null, vi = null, Oo = 0, ur = null;
  function en() {
    return (jt & 2) !== 0 && Nt !== 0 ? Nt & -Nt : lt.T !== null ? Ws() : Qd();
  }
  function Xh() {
    if (tn === 0)
      if ((Nt & 536870912) === 0 || Ot) {
        var t = xl;
        xl <<= 1, (xl & 3932160) === 0 && (xl = 262144), tn = t;
      } else tn = 536870912;
    return t = Se.current, t !== null && (t.flags |= 32), tn;
  }
  function hi(t, e) {
    if (e != null) {
      var n = t.stateNode, l = n.ref;
      l === null && (l = n.ref = Tg(
        nl(t.memoizedProps, n)
      )), mi === null && (mi = []), mi.push(e.bind(null, l));
    }
  }
  function Ge(t, e, n) {
    (t === kt && (Yt === 2 || Yt === 9) || t.cancelPendingCommit !== null) && (gi(t, 0), Vl(
      t,
      Nt,
      tn,
      !1
    )), Zi(t, n), ((jt & 2) === 0 || t !== kt) && (t === kt && ((jt & 2) === 0 && (wa |= n), ee === 4 && Vl(
      t,
      Nt,
      tn,
      !1
    )), Vn(t));
  }
  function kh(t, e, n) {
    if ((jt & 6) !== 0) throw Error(c(327));
    var l = !n && (e & 127) === 0 && (e & t.expiredLanes) === 0 || Qi(t, e), i = l ? U1(t, e) : Qs(t, e, !0), o = l;
    do {
      if (i === 0) {
        si && !l && Vl(t, e, 0, !1);
        break;
      } else {
        if (n = t.current.alternate, o && !z1(n)) {
          i = Qs(t, e, !1), o = !1;
          continue;
        }
        if (i === 2) {
          if (o = e, t.errorRecoveryDisabledLanes & o)
            var s = 0;
          else
            s = t.pendingLanes & -536870913, s = s !== 0 ? s : s & 536870912 ? 536870912 : 0;
          if (s !== 0) {
            e = s;
            t: {
              var h = t;
              i = Co;
              var T = h.current.memoizedState.isDehydrated;
              if (T && (gi(h, s).flags |= 256), s = Qs(
                h,
                s,
                !1
              ), s !== 2 && s !== 6) {
                if (qs && !T) {
                  h.errorRecoveryDisabledLanes |= o, wa |= o, i = 4;
                  break t;
                }
                o = Ve, Ve = i, o !== null && (Ve === null ? Ve = o : Ve.push.apply(
                  Ve,
                  o
                ));
              }
              i = s;
            }
            if (o = !1, i !== 2) continue;
          }
        }
        if (i === 1) {
          gi(t, 0), Vl(t, e, 0, !0);
          break;
        }
        t: {
          switch (l = t, o = i, o) {
            case 0:
            case 1:
              throw Error(c(345));
            case 4:
              if ((e & 4194048) !== e && (e & 62914560) !== e)
                break;
            case 6:
              Vl(
                l,
                e,
                tn,
                !Ll
              );
              break t;
            case 2:
              Ve = null;
              break;
            case 3:
            case 5:
              break;
            default:
              throw Error(c(329));
          }
          if ((e & 62914560) === e && (i = ar + 300 - Ae(), 10 < i)) {
            if (Vl(
              l,
              e,
              tn,
              !Ll
            ), lu(l, 0, !0) !== 0) break t;
            qn = e, l.timeoutHandle = ff(
              Qh.bind(
                null,
                l,
                n,
                Ve,
                or,
                Vs,
                e,
                tn,
                wa,
                fi,
                Ll,
                o,
                "Throttled",
                -0,
                0
              ),
              i
            );
            break t;
          }
          Qh(
            l,
            n,
            Ve,
            or,
            Vs,
            e,
            tn,
            wa,
            fi,
            Ll,
            o,
            null,
            -0,
            0
          );
        }
      }
      break;
    } while (!0);
    Vn(t);
  }
  function Qh(t, e, n, l, i, o, s, h, T, z, j, G, A, U) {
    t.timeoutHandle = -1;
    var nt = e.subtreeFlags, ct = (o & 335544064) === o;
    if (G = null, (ct || nt & 8192 || (nt & 16785408) === 16785408) && (G = {
      stylesheets: null,
      count: 0,
      imgCount: 0,
      imgBytes: 0,
      suspenseyImages: [],
      waitingForImages: !0,
      waitingForViewTransition: !1,
      unsuspend: Dn
    }, Pe = null, Bh(
      e,
      o,
      G
    ), ct && (nt = G, ct = t.containerInfo, ct = (ct.nodeType === 9 ? ct : ct.ownerDocument).__reactViewTransition, ct != null && (nt.count++, nt.waitingForViewTransition = !0, nt = Uo.bind(nt), ct.finished.then(nt, nt))), nt = (o & 62914560) === o ? ar - Ae() : (o & 4194048) === o ? Vh - Ae() : 0, nt = jS(
      G,
      nt
    ), nt !== null)) {
      qn = o, t.cancelPendingCommit = nt(
        Wh.bind(
          null,
          t,
          e,
          o,
          n,
          l,
          i,
          s,
          h,
          T,
          z,
          j,
          G,
          null,
          A,
          U
        )
      ), Vl(t, o, s, !z);
      return;
    }
    Wh(
      t,
      e,
      o,
      n,
      l,
      i,
      s,
      h,
      T,
      z,
      j,
      G
    );
  }
  function z1(t) {
    for (var e = t; ; ) {
      var n = e.tag;
      if ((n === 0 || n === 11 || n === 15) && e.flags & 16384 && (n = e.updateQueue, n !== null && (n = n.stores, n !== null)))
        for (var l = 0; l < n.length; l++) {
          var i = n[l], o = i.getSnapshot;
          i = i.value;
          try {
            if (!$e(o(), i)) return !1;
          } catch {
            return !1;
          }
        }
      if (n = e.child, e.subtreeFlags & 16384 && n !== null)
        n.return = e, e = n;
      else {
        if (e === t) break;
        for (; e.sibling === null; ) {
          if (e.return === null || e.return === t) return !0;
          e = e.return;
        }
        e.sibling.return = e.return, e = e.sibling;
      }
    }
    return !0;
  }
  function Vl(t, e, n, l) {
    e = qd(t, e), e &= ~lr, e &= ~wa, t.suspendedLanes |= e, t.pingedLanes &= ~e, l && (t.warmLanes |= e), l = t.expirationTimes;
    for (var i = e; 0 < i; ) {
      var o = 31 - Ht(i), s = 1 << o;
      l[o] = -1, i &= ~s;
    }
    n !== 0 && Gd(t, n, e);
  }
  function rr() {
    return (jt & 6) === 0 ? (_o(0), !1) : !0;
  }
  function ks() {
    if (At !== null) {
      if (Yt === 0)
        var t = At.return;
      else
        t = At, ol = da = null, Pc(t), ni = null, co = 0, t = At;
      for (; t !== null; )
        vh(t.alternate, t), t = t.return;
      At = null;
    }
  }
  function gi(t, e) {
    var n = t.timeoutHandle;
    return n !== -1 && (t.timeoutHandle = -1, nS(n)), n = t.cancelPendingCommit, n !== null && (t.cancelPendingCommit = null, n()), qn = 0, ks(), kt = t, At = n = al(t.current, null), Nt = e, Yt = 0, We = null, Ll = !1, si = Qi(t, e), qs = !1, fi = tn = lr = wa = Yl = ee = 0, Ve = Co = null, Vs = !1, dl = qd(t, e), gu(), n;
  }
  function Zh(t, e) {
    wt = null, lt.H = Vu, e === ei || e === _u ? (e = Wm(), Yt = 3) : e === Yc ? (e = Wm(), Yt = 4) : Yt = e === ms ? 8 : e !== null && typeof e == "object" && typeof e.then == "function" ? 6 : 1, We = e, At === null && (ee = 1, Gu(
      t,
      sn(e, t.current)
    ));
  }
  function Kh() {
    var t = Se.current;
    return t === null ? !0 : (Nt & 4194048) === Nt ? Ce === null : (Nt & 62914560) === Nt || (Nt & 536870912) !== 0 ? t === Ce : !1;
  }
  function Jh() {
    var t = lt.H;
    return lt.H = Vu, t === null ? Vu : t;
  }
  function Fh() {
    var t = lt.A;
    return lt.A = N1, t;
  }
  function cr() {
    ee = 4, Ll || (Nt & 4194048) !== Nt && Se.current !== null || (si = !0), (Yl & 134217727) === 0 && (wa & 134217727) === 0 || kt === null || Vl(
      kt,
      Nt,
      tn,
      !1
    );
  }
  function Qs(t, e, n) {
    var l = jt;
    jt |= 2;
    var i = Jh(), o = Fh();
    (kt !== t || Nt !== e) && (or = null, gi(t, e)), e = !1;
    var s = ee;
    t: do
      try {
        if (Yt !== 0 && At !== null) {
          var h = At, T = We;
          switch (Yt) {
            case 8:
              ks(), s = 6;
              break t;
            case 3:
            case 2:
            case 9:
            case 6:
              Se.current === null && (e = !0);
              var z = Yt;
              if (Yt = 0, We = null, yi(t, h, T, z), n && si) {
                s = 0;
                break t;
              }
              break;
            default:
              z = Yt, Yt = 0, We = null, yi(t, h, T, z);
          }
        }
        M1(), s = ee;
        break;
      } catch (j) {
        Zh(t, j);
      }
    while (!0);
    return e && t.shellSuspendCounter++, ol = da = null, jt = l, lt.H = i, lt.A = o, At === null && (kt = null, Nt = 0, gu()), s;
  }
  function M1() {
    for (; At !== null; ) $h(At);
  }
  function U1(t, e) {
    var n = jt;
    jt |= 2;
    var l = Jh(), i = Fh();
    kt !== t || Nt !== e ? (or = null, ir = Ae() + 500, gi(t, e)) : si = Qi(
      t,
      e
    );
    t: do
      try {
        if (Yt !== 0 && At !== null) {
          e = At;
          var o = We;
          e: switch (Yt) {
            case 1:
              Yt = 0, We = null, yi(t, e, o, 1);
              break;
            case 2:
            case 9:
              if (Im(o)) {
                Yt = 0, We = null, Ih(e);
                break;
              }
              e = function() {
                Yt !== 2 && Yt !== 9 || kt !== t || (Yt = 7), Vn(t);
              }, o.then(e, e);
              break t;
            case 3:
              Yt = 7;
              break t;
            case 4:
              Yt = 5;
              break t;
            case 7:
              Im(o) ? (Yt = 0, We = null, Ih(e)) : (Yt = 0, We = null, yi(t, e, o, 7));
              break;
            case 5:
              var s = null;
              switch (At.tag) {
                case 26:
                  s = At.memoizedState;
                case 5:
                case 27:
                  var h = At;
                  if (s ? Gg(s) : h.stateNode.complete) {
                    Yt = 0, We = null;
                    var T = h.sibling;
                    if (T !== null) At = T;
                    else {
                      var z = h.return;
                      z !== null ? (At = z, sr(z)) : At = null;
                    }
                    break e;
                  }
              }
              Yt = 0, We = null, yi(t, e, o, 5);
              break;
            case 6:
              Yt = 0, We = null, yi(t, e, o, 6);
              break;
            case 8:
              ks(), ee = 6;
              break t;
            default:
              throw Error(c(462));
          }
        }
        H1();
        break;
      } catch (j) {
        Zh(t, j);
      }
    while (!0);
    return ol = da = null, lt.H = l, lt.A = i, jt = n, At !== null ? 0 : (kt = null, Nt = 0, gu(), ee);
  }
  function H1() {
    for (; At !== null && !tu(); )
      $h(At);
  }
  function $h(t) {
    var e = dh(t.alternate, t, dl);
    t.memoizedProps = t.pendingProps, e === null ? sr(t) : At = e;
  }
  function Ih(t) {
    var e = t, n = e.alternate;
    switch (e.tag) {
      case 15:
      case 0:
        e = ih(
          n,
          e,
          e.pendingProps,
          e.type,
          void 0,
          Nt
        );
        break;
      case 11:
        e = ih(
          n,
          e,
          e.pendingProps,
          e.type.render,
          e.ref,
          Nt
        );
        break;
      case 5:
        Pc(e);
        var l = e;
        l === de && (Ot ? (xu(l), l.tag === 5 && l.stateNode != null && (Zt = l.stateNode)) : (xu(l), Ot = !0));
      default:
        vh(n, e), e = At = qm(e, dl), e = dh(n, e, dl);
    }
    t.memoizedProps = t.pendingProps, e === null ? sr(t) : At = e;
  }
  function yi(t, e, n, l) {
    ol = da = null, Pc(e), ni = null, co = 0;
    var i = e.return;
    try {
      if (x1(
        t,
        i,
        e,
        n,
        Nt
      )) {
        ee = 1, Gu(
          t,
          sn(n, t.current)
        ), At = null;
        return;
      }
    } catch (o) {
      if (i !== null) throw At = i, o;
      ee = 1, Gu(
        t,
        sn(n, t.current)
      ), At = null;
      return;
    }
    e.flags & 32768 ? (Ot || l === 1 ? t = !0 : si || (Nt & 536870912) !== 0 ? t = !1 : (Ll = t = !0, (l === 2 || l === 9 || l === 3 || l === 6) && (l = Se.current, l !== null && l.tag === 13 && (l.flags |= 16384))), Ph(e, t)) : sr(e);
  }
  function sr(t) {
    var e = t;
    do {
      if ((e.flags & 32768) !== 0) {
        Ph(
          e,
          Ll
        );
        return;
      }
      t = e.return;
      var n = O1(
        e.alternate,
        e,
        dl
      );
      if (n !== null) {
        At = n;
        return;
      }
      if (e = e.sibling, e !== null) {
        At = e;
        return;
      }
      At = e = t;
    } while (e !== null);
    ee === 0 && (ee = 5);
  }
  function Ph(t, e) {
    do {
      var n = _1(t.alternate, t);
      if (n !== null) {
        n.flags &= 32767, At = n;
        return;
      }
      if (n = t.return, n !== null && (n.flags |= 32768, n.subtreeFlags = 0, n.deletions = null), !e && (t = t.sibling, t !== null)) {
        At = t;
        return;
      }
      At = t = n;
    } while (t !== null);
    ee = 6, At = null;
  }
  function Wh(t, e, n, l, i, o, s, h, T, z, j, G) {
    t.cancelPendingCommit = null;
    do
      fr();
    while ($t !== 0);
    if ((jt & 6) !== 0) throw Error(c(327));
    if (e !== null) {
      if (e === t.current) throw Error(c(177));
      t === kt && (At = kt = null, Nt = 0), Ca = e, On = t, qn = n, Xs = i, Gh = l, j1(
        t,
        e,
        n,
        s,
        h,
        T,
        G
      );
    }
  }
  function j1(t, e, n, l, i, o, s) {
    var h = e.lanes | e.childLanes;
    if (Gs = h, h |= Oc, rb(
      t,
      n,
      h,
      l,
      i,
      o
    ), mi = null, (n & 335544064) === n ? (vi = s1(t), l = 10262) : (vi = null, l = 10256), (e.subtreeFlags & l) !== 0 || (e.flags & l) !== 0 ? (t.callbackNode = null, t.callbackPriority = 0, G1(Ba, function() {
      return Fs(), null;
    })) : (t.callbackNode = null, t.callbackPriority = 0), $u = !1, l = (e.flags & 13878) !== 0, (e.subtreeFlags & 13878) !== 0 || l) {
      l = lt.T, lt.T = null, i = mt.p, mt.p = 2, o = jt, jt |= 4;
      try {
        A1(t, e, n);
      } finally {
        jt = o, mt.p = i, lt.T = l;
      }
    }
    $t = 1, $u ? di = rS(
      s,
      t.containerInfo,
      vi,
      Zs,
      Ks,
      L1,
      Js,
      Fs,
      B1
    ) : (Zs(), Ks(), Js());
  }
  function B1(t) {
    if ($t !== 0) {
      var e = On.onRecoverableError;
      e(t, { componentStack: null });
    }
  }
  function L1() {
    $t === 3 && ($t = 0, Hh(Ca, On), $t = 4);
  }
  function Zs() {
    if ($t === 1) {
      $t = 0;
      var t = On, e = Ca, n = qn, l = (e.flags & 13878) !== 0;
      if ((e.subtreeFlags & 13878) !== 0 || l) {
        l = lt.T, lt.T = null;
        var i = mt.p;
        mt.p = 2;
        var o = jt;
        jt |= 4;
        try {
          xo = Wu = !1, Mh(e, t, n), n = rf;
          var s = Nm(t.containerInfo), h = n.focusedElem, T = n.selectionRange;
          if (s !== h && h && h.ownerDocument && Rm(
            h.ownerDocument.documentElement,
            h
          )) {
            if (T !== null && Ec(h)) {
              var z = T.start, j = T.end;
              if (j === void 0 && (j = z), "selectionStart" in h)
                h.selectionStart = z, h.selectionEnd = Math.min(
                  j,
                  h.value.length
                );
              else {
                var G = h.ownerDocument || document, A = G && G.defaultView || window;
                if (A.getSelection) {
                  var U = A.getSelection(), nt = h.textContent.length, ct = Math.min(T.start, nt), Ct = T.end === void 0 ? ct : Math.min(T.end, nt);
                  !U.extend && ct > Ct && (s = Ct, Ct = ct, ct = s);
                  var D = Am(
                    h,
                    ct
                  ), w = Am(
                    h,
                    Ct
                  );
                  if (D && w && (U.rangeCount !== 1 || U.anchorNode !== D.node || U.anchorOffset !== D.offset || U.focusNode !== w.node || U.focusOffset !== w.offset)) {
                    var M = G.createRange();
                    M.setStart(D.node, D.offset), U.removeAllRanges(), ct > Ct ? (U.addRange(M), U.extend(w.node, w.offset)) : (M.setEnd(w.node, w.offset), U.addRange(M));
                  }
                }
              }
            }
            for (G = [], U = h; U = U.parentNode; )
              U.nodeType === 1 && G.push({
                element: U,
                left: U.scrollLeft,
                top: U.scrollTop
              });
            for (typeof h.focus == "function" && h.focus(), h = 0; h < G.length; h++) {
              var q = G[h];
              q.element.scrollLeft = q.left, q.element.scrollTop = q.top;
            }
          }
          Ci = !!uf, rf = uf = null;
        } finally {
          jt = o, mt.p = i, lt.T = l;
        }
      }
      t.current = e, $t = 2;
    }
  }
  function Ks() {
    if ($t === 2) {
      $t = 0;
      var t = On, e = Ca, n = (e.flags & 8772) !== 0;
      if ((e.subtreeFlags & 8772) !== 0 || n) {
        n = lt.T, lt.T = null;
        var l = mt.p;
        mt.p = 2;
        var i = jt;
        jt |= 4;
        try {
          _h(t, e.alternate, e);
        } finally {
          jt = i, mt.p = l, lt.T = n;
        }
      }
      $t = 3;
    }
  }
  function Js() {
    if ($t === 4 || $t === 3) {
      $t = 0;
      var t = di;
      di = null, on();
      var e = On, n = Ca, l = qn, i = Gh, o = (l & 335544064) === l ? 10262 : 10256;
      if ((n.subtreeFlags & o) !== 0 || (n.flags & o) !== 0 ? $t = 5 : ($t = 0, Ca = On = null, tg(e, e.pendingLanes)), o = e.pendingLanes, o === 0 && (ql = null), lc(l), n = n.stateNode, Gt && typeof Gt.onCommitFiberRoot == "function")
        try {
          Gt.onCommitFiberRoot(
            Wt,
            n,
            void 0,
            (n.current.flags & 128) === 128
          );
        } catch {
        }
      if (i !== null) {
        n = lt.T, o = mt.p, mt.p = 2, lt.T = null;
        try {
          for (var s = e.onRecoverableError, h = 0; h < i.length; h++) {
            var T = i[h];
            s(T.value, {
              componentStack: T.stack
            });
          }
        } finally {
          lt.T = n, mt.p = o;
        }
      }
      if (i = mi, s = vi, vi = null, i !== null && (mi = null, s === null && (s = []), t !== null))
        for (T = 0; T < i.length; T++)
          n = (0, i[T])(
            s
          ), n !== void 0 && t.finished.finally(n);
      (qn & 3) !== 0 && fr(), Vn(e), o = e.pendingLanes, (l & 261930) !== 0 && (o & 42) !== 0 ? e === ur ? Oo++ : (Oo = 0, ur = e) : (Oo = 0, ur = null), _o(0);
    }
  }
  function tg(t, e) {
    (t.pooledCacheLanes &= e) === 0 && (e = t.pooledCache, e != null && (t.pooledCache = null, oo(e)));
  }
  function fr() {
    return di !== null && (di.skipTransition(), di = null), Zs(), Ks(), Js(), Fs();
  }
  function Fs() {
    if ($t !== 5) return !1;
    var t = On, e = Gs;
    Gs = 0;
    var n = lc(qn), l = lt.T, i = mt.p;
    try {
      mt.p = 32 > n ? 32 : n, lt.T = null, n = Xs, Xs = null;
      var o = On, s = qn;
      if ($t = 0, Ca = On = null, qn = 0, (jt & 6) !== 0) throw Error(c(331));
      var h = jt;
      if (jt |= 4, Yh(o.current), jh(
        o,
        o.current,
        s,
        n
      ), jt = h, _o(0, !1), Gt && typeof Gt.onPostCommitFiberRoot == "function")
        try {
          Gt.onPostCommitFiberRoot(Wt, o);
        } catch {
        }
      return !0;
    } finally {
      mt.p = i, lt.T = l, tg(t, e);
    }
  }
  function eg(t, e, n) {
    e = sn(n, e), e = ds(t.stateNode, e, 2), t = zl(t, e, 2), t !== null && (Zi(t, 2), Vn(t));
  }
  function qt(t, e, n) {
    if (t.tag === 3)
      eg(t, t, n);
    else
      for (; e !== null; ) {
        if (e.tag === 3) {
          eg(
            e,
            t,
            n
          );
          break;
        } else if (e.tag === 1) {
          var l = e.stateNode;
          if (typeof e.type.getDerivedStateFromError == "function" || typeof l.componentDidCatch == "function" && (ql === null || !ql.has(l))) {
            t = sn(n, t), n = Iv(2), l = zl(e, n, 2), l !== null && (Pv(
              n,
              l,
              e,
              t
            ), Zi(l, 2), Vn(l));
            break;
          }
        }
        e = e.return;
      }
  }
  function $s(t, e, n) {
    var l = t.pingCache;
    if (l === null) {
      l = t.pingCache = new D1();
      var i = /* @__PURE__ */ new Set();
      l.set(e, i);
    } else
      i = l.get(e), i === void 0 && (i = /* @__PURE__ */ new Set(), l.set(e, i));
    i.has(n) || (qs = !0, i.add(n), t = Y1.bind(null, t, e, n), e.then(t, t));
  }
  function Y1(t, e, n) {
    var l = t.pingCache;
    l !== null && l.delete(e), t.pingedLanes |= t.suspendedLanes & n, t.warmLanes &= ~n, kt === t && (Nt & n) === n && ((ee === 4 || ee === 3 && (Nt & 62914560) === Nt && 300 > Ae() - ar) && (jt & 2) === 0 ? gi(t, 0) : lr |= n, fi === Nt && (fi = 0)), Vn(t);
  }
  function ng(t, e) {
    e === 0 && (e = Vd()), t = ca(t, e), t !== null && (Zi(t, e), Vn(t));
  }
  function q1(t) {
    var e = t.memoizedState, n = 0;
    e !== null && (n = e.retryLane), ng(t, n);
  }
  function V1(t, e) {
    var n = 0;
    switch (t.tag) {
      case 31:
      case 13:
        var l = t.stateNode, i = t.memoizedState;
        i !== null && (n = i.retryLane);
        break;
      case 19:
        l = t.stateNode;
        break;
      case 22:
        l = t.stateNode._retryCache;
        break;
      default:
        throw Error(c(314));
    }
    l !== null && l.delete(e), ng(t, n);
  }
  function G1(t, e) {
    return qi(t, e);
  }
  var pi = null, bi = null, Is = !1, dr = !1, Ps = !1, Gl = 0;
  function Vn(t) {
    t !== bi && t.next === null && (bi === null ? pi = bi = t : bi = bi.next = t), dr = !0, Is || (Is = !0, k1());
  }
  function _o(t, e) {
    if (!Ps && dr) {
      Ps = !0;
      do
        for (var n = !1, l = pi; l !== null; ) {
          if (t !== 0) {
            var i = l.pendingLanes;
            if (i === 0) var o = 0;
            else {
              var s = l.suspendedLanes, h = l.pingedLanes;
              o = (1 << 31 - Ht(42 | t) + 1) - 1, o &= i & ~(s & ~h), o = o & 201326741 ? o & 201326741 | 1 : o ? o | 2 : 0;
            }
            o !== 0 && (n = !0, og(l, o));
          } else
            o = Nt, o = lu(
              l,
              l === kt ? o : 0,
              l.cancelPendingCommit !== null || l.timeoutHandle !== -1
            ), (o & 3) === 0 || Qi(l, o) || (n = !0, og(l, o));
          l = l.next;
        }
      while (n);
      Ps = !1;
    }
  }
  function X1() {
    lg();
  }
  function lg() {
    dr = Is = !1;
    var t = 0;
    Gl !== 0 && eS() && (t = Gl);
    for (var e = Ae(), n = null, l = pi; l !== null; ) {
      var i = l.next, o = ag(l, e);
      o === 0 ? (l.next = null, n === null ? pi = i : n.next = i, i === null && (bi = n)) : (n = l, (t !== 0 || (o & 3) !== 0) && (dr = !0)), l = i;
    }
    $t !== 0 && $t !== 5 || _o(t), Gl !== 0 && (Gl = 0);
  }
  function ag(t, e) {
    for (var n = t.suspendedLanes, l = t.pingedLanes, i = t.expirationTimes, o = t.pendingLanes & -62914561; 0 < o; ) {
      var s = 31 - Ht(o), h = 1 << s, T = i[s];
      T === -1 ? ((h & n) === 0 || (h & l) !== 0) && (i[s] = ub(h, e)) : T <= e && (t.expiredLanes |= h), o &= ~h;
    }
    if (e = kt, n = Nt, n = lu(
      t,
      t === e ? n : 0,
      t.cancelPendingCommit !== null || t.timeoutHandle !== -1
    ), l = t.callbackNode, n === 0 || t === e && (Yt === 2 || Yt === 9) || t.cancelPendingCommit !== null)
      return l !== null && l !== null && ja(l), t.callbackNode = null, t.callbackPriority = 0;
    if ((n & 3) === 0 || Qi(t, n)) {
      if (e = n & -n, e === t.callbackPriority) return e;
      switch (l !== null && ja(l), lc(n)) {
        case 2:
        case 8:
          n = Gi;
          break;
        case 32:
          n = Ba;
          break;
        case 268435456:
          n = Xi;
          break;
        default:
          n = Ba;
      }
      return l = ig.bind(null, t), n = qi(n, l), t.callbackPriority = e, t.callbackNode = n, e;
    }
    return l !== null && l !== null && ja(l), t.callbackPriority = 2, t.callbackNode = null, 2;
  }
  function ig(t, e) {
    if ($t !== 0 && $t !== 5)
      return t.callbackNode = null, t.callbackPriority = 0, null;
    var n = t.callbackNode;
    if (fr() && t.callbackNode !== n)
      return null;
    var l = Nt;
    return l = lu(
      t,
      t === kt ? l : 0,
      t.cancelPendingCommit !== null || t.timeoutHandle !== -1
    ), l === 0 ? null : (kh(t, l, e), ag(t, Ae()), t.callbackNode != null && t.callbackNode === n ? ig.bind(null, t) : null);
  }
  function og(t, e) {
    if (fr()) return null;
    kh(t, e, !0);
  }
  function k1() {
    lS(function() {
      (jt & 6) !== 0 ? qi(
        En,
        X1
      ) : lg();
    });
  }
  function Ws() {
    if (Gl === 0) {
      var t = ha;
      t === 0 && (t = Re, Re <<= 1, (Re & 261888) === 0 && (Re = 256)), Gl = t;
    }
    return Gl;
  }
  function ug(t) {
    return t == null || typeof t == "symbol" || typeof t == "boolean" ? null : typeof t == "function" ? t : ru(t);
  }
  function Q1(t, e, n, l, i) {
    if (e === "submit" && n && n.stateNode === i) {
      var o = ug(
        (i[Be] || null).action
      ), s = l.submitter;
      s && (e = (e = s[Be] || null) ? ug(e.formAction) : s.getAttribute("formAction"), e !== null && (o = e, s = null));
      var h = new du(
        "action",
        "action",
        null,
        l,
        i
      );
      t.push({
        event: h,
        listeners: [
          {
            instance: null,
            listener: function() {
              if (l.defaultPrevented) {
                if (Gl !== 0) {
                  var T = new FormData(i, s);
                  us(
                    n,
                    {
                      pending: !0,
                      data: T,
                      method: i.method,
                      action: o
                    },
                    null,
                    T
                  );
                }
              } else
                typeof o == "function" && (h.preventDefault(), T = new FormData(i, s), us(
                  n,
                  {
                    pending: !0,
                    data: T,
                    method: i.method,
                    action: o
                  },
                  o,
                  T
                ));
            },
            currentTarget: i
          }
        ]
      });
    }
  }
  for (var tf = 0; tf < Cc.length; tf++) {
    var ef = Cc[tf], Z1 = ef.toLowerCase(), K1 = ef[0].toUpperCase() + ef.slice(1);
    xn(
      Z1,
      "on" + K1
    );
  }
  xn(Mm, "onAnimationEnd"), xn(Um, "onAnimationIteration"), xn(Hm, "onAnimationStart"), xn("dblclick", "onDoubleClick"), xn("focusin", "onFocus"), xn("focusout", "onBlur"), xn(n1, "onTransitionRun"), xn(l1, "onTransitionStart"), xn(a1, "onTransitionCancel"), xn(jm, "onTransitionEnd"), Va("onMouseEnter", ["mouseout", "mouseover"]), Va("onMouseLeave", ["mouseout", "mouseover"]), Va("onPointerEnter", ["pointerout", "pointerover"]), Va("onPointerLeave", ["pointerout", "pointerover"]), oa(
    "onChange",
    "change click focusin focusout input keydown keyup selectionchange".split(" ")
  ), oa(
    "onSelect",
    "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(
      " "
    )
  ), oa("onBeforeInput", [
    "compositionend",
    "keypress",
    "textInput",
    "paste"
  ]), oa(
    "onCompositionEnd",
    "compositionend focusout keydown keypress keyup mousedown".split(" ")
  ), oa(
    "onCompositionStart",
    "compositionstart focusout keydown keypress keyup mousedown".split(" ")
  ), oa(
    "onCompositionUpdate",
    "compositionupdate focusout keydown keypress keyup mousedown".split(" ")
  );
  var Ao = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
    " "
  ), J1 = new Set(
    "beforetoggle cancel close invalid load scroll scrollend toggle".split(" ").concat(Ao)
  );
  function rg(t, e) {
    e = (e & 4) !== 0;
    for (var n = 0; n < t.length; n++) {
      var l = t[n], i = l.event;
      l = l.listeners;
      t: {
        var o = void 0;
        if (e)
          for (var s = l.length - 1; 0 <= s; s--) {
            var h = l[s], T = h.instance, z = h.currentTarget;
            if (h = h.listener, T !== o && i.isPropagationStopped())
              break t;
            o = h, i.currentTarget = z;
            try {
              o(i);
            } catch (j) {
              hu(j);
            }
            i.currentTarget = null, o = T;
          }
        else
          for (s = 0; s < l.length; s++) {
            if (h = l[s], T = h.instance, z = h.currentTarget, h = h.listener, T !== o && i.isPropagationStopped())
              break t;
            o = h, i.currentTarget = z;
            try {
              o(i);
            } catch (j) {
              hu(j);
            }
            i.currentTarget = null, o = T;
          }
      }
    }
  }
  function Rt(t, e) {
    var n = e[Kd];
    n === void 0 && (n = e[Kd] = /* @__PURE__ */ new Set());
    var l = t + "__bubble";
    n.has(l) || (cg(e, t, 2, !1), n.add(l));
  }
  function nf(t, e, n) {
    var l = 0;
    e && (l |= 4), cg(
      n,
      t,
      l,
      e
    );
  }
  var mr = "_reactListening" + Math.random().toString(36).slice(2);
  function lf(t) {
    if (!t[mr]) {
      t[mr] = !0, $d.forEach(function(n) {
        n !== "selectionchange" && (J1.has(n) || nf(n, !1, t), nf(n, !0, t));
      });
      var e = t.nodeType === 9 ? t : t.ownerDocument;
      e === null || e[mr] || (e[mr] = !0, nf("selectionchange", !1, e));
    }
  }
  function cg(t, e, n, l) {
    switch (Pg(e)) {
      case 2:
        var i = qS;
        break;
      case 8:
        i = VS;
        break;
      default:
        i = wf;
    }
    n = i.bind(
      null,
      e,
      n,
      t
    ), i = void 0, !fc || e !== "touchstart" && e !== "touchmove" && e !== "wheel" || (i = !0), l ? i !== void 0 ? t.addEventListener(e, n, {
      capture: !0,
      passive: i
    }) : t.addEventListener(e, n, !0) : i !== void 0 ? t.addEventListener(e, n, {
      passive: i
    }) : t.addEventListener(e, n, !1);
  }
  function af(t, e, n, l, i) {
    var o = l;
    if ((e & 1) === 0 && (e & 2) === 0 && l !== null)
      t: for (; ; ) {
        if (l === null) return;
        var s = l.tag;
        if (s === 3 || s === 4) {
          var h = l.stateNode.containerInfo;
          if (h === i) break;
          if (s === 4)
            for (s = l.return; s !== null; ) {
              var T = s.tag;
              if ((T === 3 || T === 4) && s.stateNode.containerInfo === i)
                return;
              s = s.return;
            }
          for (; h !== null; ) {
            if (s = ia(h), s === null) return;
            if (T = s.tag, T === 5 || T === 6 || T === 26 || T === 27) {
              l = o = s;
              continue t;
            }
            h = h.parentNode;
          }
        }
        l = l.return;
      }
    cm(function() {
      var z = o, j = cc(n), G = [];
      t: {
        var A = Bm.get(t);
        if (A !== void 0) {
          var U = du, nt = t;
          switch (t) {
            case "keypress":
              if (su(n) === 0) break t;
            case "keydown":
            case "keyup":
              U = zb;
              break;
            case "focusin":
              nt = "focus", U = hc;
              break;
            case "focusout":
              nt = "blur", U = hc;
              break;
            case "beforeblur":
            case "afterblur":
              U = hc;
              break;
            case "click":
              if (n.button === 2) break t;
            case "auxclick":
            case "dblclick":
            case "mousedown":
            case "mousemove":
            case "mouseup":
            case "mouseout":
            case "mouseover":
            case "contextmenu":
              U = dm;
              break;
            case "drag":
            case "dragend":
            case "dragenter":
            case "dragexit":
            case "dragleave":
            case "dragover":
            case "dragstart":
            case "drop":
              U = Sb;
              break;
            case "touchcancel":
            case "touchend":
            case "touchmove":
            case "touchstart":
              U = Bb;
              break;
            case Mm:
            case Um:
            case Hm:
              U = Tb;
              break;
            case jm:
              U = Yb;
              break;
            case "scroll":
            case "scrollend":
              U = pb;
              break;
            case "wheel":
              U = Vb;
              break;
            case "copy":
            case "cut":
            case "paste":
              U = Cb;
              break;
            case "gotpointercapture":
            case "lostpointercapture":
            case "pointercancel":
            case "pointerdown":
            case "pointermove":
            case "pointerout":
            case "pointerover":
            case "pointerup":
              U = vm;
              break;
            case "submit":
              U = Hb;
              break;
            case "toggle":
            case "beforetoggle":
              U = Xb;
          }
          var ct = (e & 4) !== 0, Ct = !ct && (t === "scroll" || t === "scrollend"), D = ct ? A !== null ? A + "Capture" : null : A;
          ct = [];
          for (var w = z, M; w !== null; ) {
            var q = w;
            if (M = q.stateNode, q = q.tag, q !== 5 && q !== 26 && q !== 27 || M === null || D === null || (q = Fi(w, D), q != null && ct.push(
              Ro(w, q, M)
            )), Ct) break;
            w = w.return;
          }
          0 < ct.length && (A = new U(
            A,
            nt,
            null,
            n,
            j
          ), G.push({ event: A, listeners: ct }));
        }
      }
      if ((e & 7) === 0) {
        t: {
          if (U = t === "mouseover" || t === "pointerover", A = t === "mouseout" || t === "pointerout", U && n !== rc && (nt = n.relatedTarget || n.fromElement) && (ia(nt) || nt[La]))
            break t;
          (A || U) && (nt = j.window === j ? j : (U = j.ownerDocument) ? U.defaultView || U.parentWindow : window, A ? (U = n.relatedTarget || n.toElement, A = z, U = U ? ia(U) : null, U !== null && (Ct = m(U), ct = U.tag, U !== Ct || ct !== 5 && ct !== 27 && ct !== 6) && (U = null)) : (A = null, U = z), A !== U && (ct = dm, q = "onMouseLeave", D = "onMouseEnter", w = "mouse", (t === "pointerout" || t === "pointerover") && (ct = vm, q = "onPointerLeave", D = "onPointerEnter", w = "pointer"), Ct = A == null ? nt : Ji(A), M = U == null ? nt : Ji(U), nt = new ct(
            q,
            w + "leave",
            A,
            n,
            j
          ), nt.target = Ct, nt.relatedTarget = M, q = null, ia(j) === z && (ct = new ct(
            D,
            w + "enter",
            U,
            n,
            j
          ), ct.target = M, ct.relatedTarget = Ct, q = ct), Ct = q, ct = A && U ? Z(
            A,
            U,
            F1
          ) : null, A !== null && sg(
            G,
            nt,
            A,
            ct,
            !1
          ), U !== null && Ct !== null && sg(
            G,
            Ct,
            U,
            ct,
            !0
          )));
        }
        t: {
          if (A = z ? Ji(z) : window, U = A.nodeName && A.nodeName.toLowerCase(), U === "select" || U === "input" && A.type === "file")
            var it = xm;
          else if (Sm(A))
            if (Tm)
              it = Wb;
            else {
              it = Ib;
              var Dt = $b;
            }
          else
            U = A.nodeName, !U || U.toLowerCase() !== "input" || A.type !== "checkbox" && A.type !== "radio" ? z && uc(z.elementType) && (it = xm) : it = Pb;
          if (it && (it = it(t, z))) {
            Em(
              G,
              it,
              n,
              j
            );
            break t;
          }
          Dt && Dt(t, A, z);
        }
        switch (Dt = z ? Ji(z) : window, t) {
          case "focusin":
            (Sm(Dt) || Dt.contentEditable === "true") && (Ka = Dt, xc = z, lo = null);
            break;
          case "focusout":
            lo = xc = Ka = null;
            break;
          case "mousedown":
            Tc = !0;
            break;
          case "contextmenu":
          case "mouseup":
          case "dragend":
            Tc = !1, Dm(G, n, j);
            break;
          case "selectionchange":
            if (e1) break;
          case "keydown":
          case "keyup":
            Dm(G, n, j);
        }
        var vt;
        if (yc)
          t: {
            switch (t) {
              case "compositionstart":
                var pt = "onCompositionStart";
                break t;
              case "compositionend":
                pt = "onCompositionEnd";
                break t;
              case "compositionupdate":
                pt = "onCompositionUpdate";
                break t;
            }
            pt = void 0;
          }
        else
          Za ? pm(t, n) && (pt = "onCompositionEnd") : t === "keydown" && n.keyCode === 229 && (pt = "onCompositionStart");
        pt && (hm && n.locale !== "ko" && (Za || pt !== "onCompositionStart" ? pt === "onCompositionEnd" && Za && (vt = sm()) : (Tl = j, dc = "value" in Tl ? Tl.value : Tl.textContent, Za = !0)), Dt = vr(z, pt), 0 < Dt.length && (pt = new mm(
          pt,
          t,
          null,
          n,
          j
        ), G.push({ event: pt, listeners: Dt }), vt ? pt.data = vt : (vt = bm(n), vt !== null && (pt.data = vt)))), (vt = Qb ? Zb(t, n) : Kb(t, n)) && (pt = vr(z, "onBeforeInput"), 0 < pt.length && (Dt = new mm(
          "onBeforeInput",
          "beforeinput",
          null,
          n,
          j
        ), G.push({
          event: Dt,
          listeners: pt
        }), Dt.data = vt)), Q1(
          G,
          t,
          z,
          n,
          j
        );
      }
      rg(G, e);
    });
  }
  function Ro(t, e, n) {
    return {
      instance: t,
      listener: e,
      currentTarget: n
    };
  }
  function vr(t, e) {
    for (var n = e + "Capture", l = []; t !== null; ) {
      var i = t, o = i.stateNode;
      if (i = i.tag, i !== 5 && i !== 26 && i !== 27 || o === null || (i = Fi(t, n), i != null && l.unshift(
        Ro(t, i, o)
      ), i = Fi(t, e), i != null && l.push(
        Ro(t, i, o)
      )), t.tag === 3) return l;
      t = t.return;
    }
    return [];
  }
  function F1(t) {
    if (t === null) return null;
    do
      t = t.return;
    while (t && t.tag !== 5 && t.tag !== 27);
    return t || null;
  }
  function sg(t, e, n, l, i) {
    for (var o = e._reactName, s = []; n !== null && n !== l; ) {
      var h = n, T = h.alternate, z = h.stateNode;
      if (h = h.tag, T !== null && T === l) break;
      h !== 5 && h !== 26 && h !== 27 || z === null || (T = z, i ? (z = Fi(n, o), z != null && s.unshift(
        Ro(n, z, T)
      )) : i || (z = Fi(n, o), z != null && s.push(
        Ro(n, z, T)
      ))), n = n.return;
    }
    s.length !== 0 && t.push({ event: e, listeners: s });
  }
  var $1 = /\r\n?/g, I1 = /\u0000|\uFFFD/g;
  function fg(t) {
    return (typeof t == "string" ? t : "" + t).replace($1, `
`).replace(I1, "");
  }
  function dg(t, e) {
    return e = fg(e), fg(t) === e;
  }
  function Vt(t, e, n, l, i, o) {
    switch (n) {
      case "children":
        if (typeof l == "string")
          e === "body" || e === "textarea" && l === "" || Xa(t, l);
        else if (typeof l == "number" || typeof l == "bigint")
          e !== "body" && Xa(t, "" + l);
        else return;
        break;
      case "className":
        uu(t, "class", l);
        break;
      case "tabIndex":
        uu(t, "tabindex", l);
        break;
      case "dir":
      case "role":
      case "viewBox":
      case "width":
      case "height":
        uu(t, n, l);
        break;
      case "style":
        um(t, l, o);
        return;
      case "data":
        if (e !== "object") {
          uu(t, "data", l);
          break;
        }
      case "src":
      case "href":
        if (l === "" && (e !== "a" || n !== "href")) {
          t.removeAttribute(n);
          break;
        }
        if (l == null || typeof l == "function" || typeof l == "symbol" || typeof l == "boolean") {
          t.removeAttribute(n);
          break;
        }
        l = ru(l), t.setAttribute(n, l);
        break;
      case "action":
      case "formAction":
        if (typeof l == "function") {
          t.setAttribute(
            n,
            "javascript:throw new Error('A React form was unexpectedly submitted. If you called form.submit() manually, consider using form.requestSubmit() instead. If you\\'re trying to use event.stopPropagation() in a submit event handler, consider also calling event.preventDefault().')"
          );
          break;
        } else
          typeof o == "function" && (n === "formAction" ? (e !== "input" && Vt(t, e, "name", i.name, i, null), Vt(
            t,
            e,
            "formEncType",
            i.formEncType,
            i,
            null
          ), Vt(
            t,
            e,
            "formMethod",
            i.formMethod,
            i,
            null
          ), Vt(
            t,
            e,
            "formTarget",
            i.formTarget,
            i,
            null
          )) : (Vt(t, e, "encType", i.encType, i, null), Vt(t, e, "method", i.method, i, null), Vt(t, e, "target", i.target, i, null)));
        if (l == null || typeof l == "symbol" || typeof l == "boolean") {
          t.removeAttribute(n);
          break;
        }
        l = ru(l), t.setAttribute(n, l);
        break;
      case "onClick":
        l != null && (t.onclick = Dn);
        return;
      case "onScroll":
        l != null && Rt("scroll", t);
        return;
      case "onScrollEnd":
        l != null && Rt("scrollend", t);
        return;
      case "dangerouslySetInnerHTML":
        if (l != null) {
          if (typeof l != "object" || !("__html" in l))
            throw Error(c(61));
          if (n = l.__html, n != null) {
            if (i.children != null) throw Error(c(60));
            (o != null ? o.__html : void 0) !== n && (t.innerHTML = n);
          }
        }
        break;
      case "multiple":
        t.multiple = l && typeof l != "function" && typeof l != "symbol";
        break;
      case "muted":
        t.muted = l && typeof l != "function" && typeof l != "symbol";
        break;
      case "suppressContentEditableWarning":
      case "suppressHydrationWarning":
      case "defaultValue":
      case "defaultChecked":
      case "innerHTML":
      case "ref":
        break;
      case "autoFocus":
        break;
      case "xlinkHref":
        if (l == null || typeof l == "function" || typeof l == "boolean" || typeof l == "symbol") {
          t.removeAttribute("xlink:href");
          break;
        }
        n = ru(l), t.setAttributeNS(
          "http://www.w3.org/1999/xlink",
          "xlink:href",
          n
        );
        break;
      case "contentEditable":
      case "spellCheck":
      case "draggable":
      case "value":
      case "autoReverse":
      case "externalResourcesRequired":
      case "focusable":
      case "preserveAlpha":
        l != null && typeof l != "function" && typeof l != "symbol" ? t.setAttribute(n, l) : t.removeAttribute(n);
        break;
      case "inert":
      case "allowFullScreen":
      case "async":
      case "autoPlay":
      case "controls":
      case "credentialless":
      case "default":
      case "defer":
      case "disabled":
      case "disablePictureInPicture":
      case "disableRemotePlayback":
      case "formNoValidate":
      case "hidden":
      case "loop":
      case "noModule":
      case "noValidate":
      case "open":
      case "playsInline":
      case "readOnly":
      case "required":
      case "reversed":
      case "scoped":
      case "seamless":
      case "itemScope":
        l && typeof l != "function" && typeof l != "symbol" ? t.setAttribute(n, "") : t.removeAttribute(n);
        break;
      case "capture":
      case "download":
        l === !0 ? t.setAttribute(n, "") : l !== !1 && l != null && typeof l != "function" && typeof l != "symbol" ? t.setAttribute(n, l) : t.removeAttribute(n);
        break;
      case "cols":
      case "rows":
      case "size":
      case "span":
        l != null && typeof l != "function" && typeof l != "symbol" && !isNaN(l) && 1 <= l ? t.setAttribute(n, l) : t.removeAttribute(n);
        break;
      case "rowSpan":
      case "start":
        l == null || typeof l == "function" || typeof l == "symbol" || isNaN(l) ? t.removeAttribute(n) : t.setAttribute(n, l);
        break;
      case "popover":
        Rt("beforetoggle", t), Rt("toggle", t), ou(t, "popover", l);
        break;
      case "xlinkActuate":
        tl(
          t,
          "http://www.w3.org/1999/xlink",
          "xlink:actuate",
          l
        );
        break;
      case "xlinkArcrole":
        tl(
          t,
          "http://www.w3.org/1999/xlink",
          "xlink:arcrole",
          l
        );
        break;
      case "xlinkRole":
        tl(
          t,
          "http://www.w3.org/1999/xlink",
          "xlink:role",
          l
        );
        break;
      case "xlinkShow":
        tl(
          t,
          "http://www.w3.org/1999/xlink",
          "xlink:show",
          l
        );
        break;
      case "xlinkTitle":
        tl(
          t,
          "http://www.w3.org/1999/xlink",
          "xlink:title",
          l
        );
        break;
      case "xlinkType":
        tl(
          t,
          "http://www.w3.org/1999/xlink",
          "xlink:type",
          l
        );
        break;
      case "xmlBase":
        tl(
          t,
          "http://www.w3.org/XML/1998/namespace",
          "xml:base",
          l
        );
        break;
      case "xmlLang":
        tl(
          t,
          "http://www.w3.org/XML/1998/namespace",
          "xml:lang",
          l
        );
        break;
      case "xmlSpace":
        tl(
          t,
          "http://www.w3.org/XML/1998/namespace",
          "xml:space",
          l
        );
        break;
      case "is":
        ou(t, "is", l);
        break;
      case "innerText":
      case "textContent":
        return;
      default:
        if (!(2 < n.length) || n[0] !== "o" && n[0] !== "O" || n[1] !== "n" && n[1] !== "N")
          n = gb.get(n) || n, ou(t, n, l);
        else return;
    }
    Mt = !0;
  }
  function of(t, e, n, l, i, o) {
    switch (n) {
      case "style":
        um(t, l, o);
        return;
      case "dangerouslySetInnerHTML":
        if (l != null) {
          if (typeof l != "object" || !("__html" in l))
            throw Error(c(61));
          if (n = l.__html, n != null) {
            if (i.children != null) throw Error(c(60));
            (o != null ? o.__html : void 0) !== n && (t.innerHTML = n);
          }
        }
        break;
      case "children":
        if (typeof l == "string") Xa(t, l);
        else if (typeof l == "number" || typeof l == "bigint")
          Xa(t, "" + l);
        else return;
        break;
      case "onScroll":
        l != null && Rt("scroll", t);
        return;
      case "onScrollEnd":
        l != null && Rt("scrollend", t);
        return;
      case "onClick":
        l != null && (t.onclick = Dn);
        return;
      case "suppressContentEditableWarning":
      case "suppressHydrationWarning":
      case "innerHTML":
      case "ref":
        return;
      case "innerText":
      case "textContent":
        return;
      default:
        if (!Id.hasOwnProperty(n))
          t: {
            if (n[0] === "o" && n[1] === "n" && (i = n.endsWith("Capture"), o = n.slice(2, i ? n.length - 7 : void 0), e = t[Be] || null, e = e != null ? e[n] : null, typeof e == "function" && t.removeEventListener(o, e, i), typeof l == "function")) {
              typeof e != "function" && e !== null && (n in t ? t[n] = null : t.hasAttribute(n) && t.removeAttribute(n)), t.addEventListener(o, l, i);
              break t;
            }
            Mt = !0, n in t ? t[n] = l : l === !0 ? t.setAttribute(n, "") : ou(t, n, l);
          }
        return;
    }
    Mt = !0;
  }
  function Te(t, e, n) {
    switch (e) {
      case "div":
      case "span":
      case "svg":
      case "path":
      case "a":
      case "g":
      case "p":
      case "li":
        break;
      case "img":
        Rt("error", t), Rt("load", t);
        var l = !1, i = !1, o;
        for (o in n)
          if (n.hasOwnProperty(o)) {
            var s = n[o];
            if (s != null)
              switch (o) {
                case "src":
                  l = !0;
                  break;
                case "srcSet":
                  i = !0;
                  break;
                case "children":
                case "dangerouslySetInnerHTML":
                  throw Error(c(137, e));
                default:
                  Vt(t, e, o, s, n, null);
              }
          }
        i && Vt(t, e, "srcSet", n.srcSet, n, null), l && Vt(t, e, "src", n.src, n, null);
        return;
      case "input":
        Rt("invalid", t);
        var h = o = s = i = null, T = null, z = null;
        for (l in n)
          if (n.hasOwnProperty(l)) {
            var j = n[l];
            if (j != null)
              switch (l) {
                case "name":
                  i = j;
                  break;
                case "type":
                  s = j;
                  break;
                case "checked":
                  T = j;
                  break;
                case "defaultChecked":
                  z = j;
                  break;
                case "value":
                  o = j;
                  break;
                case "defaultValue":
                  h = j;
                  break;
                case "children":
                case "dangerouslySetInnerHTML":
                  if (j != null)
                    throw Error(c(137, e));
                  break;
                default:
                  Vt(t, e, l, j, n, null);
              }
          }
        lm(
          t,
          o,
          h,
          T,
          z,
          s,
          i,
          !1
        );
        return;
      case "select":
        Rt("invalid", t), l = s = o = null;
        for (i in n)
          if (n.hasOwnProperty(i) && (h = n[i], h != null))
            switch (i) {
              case "value":
                o = h;
                break;
              case "defaultValue":
                s = h;
                break;
              case "multiple":
                l = h;
              default:
                Vt(t, e, i, h, n, null);
            }
        e = o, n = s, t.multiple = !!l, e != null ? Ga(t, !!l, e, !1) : n != null && Ga(t, !!l, n, !0);
        return;
      case "textarea":
        Rt("invalid", t), o = i = l = null;
        for (s in n)
          if (n.hasOwnProperty(s) && (h = n[s], h != null))
            switch (s) {
              case "value":
                l = h;
                break;
              case "defaultValue":
                i = h;
                break;
              case "children":
                o = h;
                break;
              case "dangerouslySetInnerHTML":
                if (h != null) throw Error(c(91));
                break;
              default:
                Vt(t, e, s, h, n, null);
            }
        im(t, l, i, o);
        return;
      case "option":
        for (T in n)
          if (n.hasOwnProperty(T) && (l = n[T], l != null))
            switch (T) {
              case "selected":
                t.selected = l && typeof l != "function" && typeof l != "symbol";
                break;
              default:
                Vt(t, e, T, l, n, null);
            }
        return;
      case "dialog":
        Rt("beforetoggle", t), Rt("toggle", t), Rt("cancel", t), Rt("close", t);
        break;
      case "iframe":
      case "object":
        Rt("load", t);
        break;
      case "video":
      case "audio":
        for (l = 0; l < Ao.length; l++)
          Rt(Ao[l], t);
        break;
      case "image":
        Rt("error", t), Rt("load", t);
        break;
      case "details":
        Rt("toggle", t);
        break;
      case "embed":
      case "source":
      case "link":
        Rt("error", t), Rt("load", t);
      case "area":
      case "base":
      case "br":
      case "col":
      case "hr":
      case "keygen":
      case "meta":
      case "param":
      case "track":
      case "wbr":
      case "menuitem":
        for (z in n)
          if (n.hasOwnProperty(z) && (l = n[z], l != null))
            switch (z) {
              case "children":
              case "dangerouslySetInnerHTML":
                throw Error(c(137, e));
              default:
                Vt(t, e, z, l, n, null);
            }
        return;
      default:
        if (uc(e)) {
          for (j in n)
            n.hasOwnProperty(j) && (l = n[j], l !== void 0 && of(
              t,
              e,
              j,
              l,
              n,
              void 0
            ));
          return;
        }
    }
    for (h in n)
      n.hasOwnProperty(h) && (l = n[h], l != null && Vt(t, e, h, l, n, null));
  }
  var P1 = {};
  function W1(t, e, n, l) {
    switch (e) {
      case "div":
      case "span":
      case "svg":
      case "path":
      case "a":
      case "g":
      case "p":
      case "li":
        break;
      case "input":
        var i = null, o = null, s = null, h = null, T = null, z = null, j = null;
        for (U in n) {
          var G = n[U];
          if (n.hasOwnProperty(U) && G != null)
            switch (U) {
              case "checked":
                break;
              case "value":
                break;
              case "defaultValue":
                T = G;
              default:
                l.hasOwnProperty(U) || Vt(t, e, U, null, l, G);
            }
        }
        for (var A in l) {
          var U = l[A];
          if (G = n[A], l.hasOwnProperty(A) && (U != null || G != null))
            switch (A) {
              case "type":
                U !== G && (Mt = !0), o = U;
                break;
              case "name":
                U !== G && (Mt = !0), i = U;
                break;
              case "checked":
                U !== G && (Mt = !0), z = U;
                break;
              case "defaultChecked":
                U !== G && (Mt = !0), j = U;
                break;
              case "value":
                U !== G && (Mt = !0), s = U;
                break;
              case "defaultValue":
                U !== G && (Mt = !0), h = U;
                break;
              case "children":
              case "dangerouslySetInnerHTML":
                if (U != null)
                  throw Error(c(137, e));
                break;
              default:
                U !== G && Vt(
                  t,
                  e,
                  A,
                  U,
                  l,
                  G
                );
            }
        }
        ic(
          t,
          s,
          h,
          T,
          z,
          j,
          o,
          i
        );
        return;
      case "select":
        U = s = h = A = null;
        for (o in n)
          if (T = n[o], n.hasOwnProperty(o) && T != null)
            switch (o) {
              case "value":
                break;
              case "multiple":
                U = T;
              default:
                l.hasOwnProperty(o) || Vt(
                  t,
                  e,
                  o,
                  null,
                  l,
                  T
                );
            }
        for (i in l)
          if (o = l[i], T = n[i], l.hasOwnProperty(i) && (o != null || T != null))
            switch (i) {
              case "value":
                o !== T && (Mt = !0), A = o;
                break;
              case "defaultValue":
                o !== T && (Mt = !0), h = o;
                break;
              case "multiple":
                o !== T && (Mt = !0), s = o;
              default:
                o !== T && Vt(
                  t,
                  e,
                  i,
                  o,
                  l,
                  T
                );
            }
        e = h, n = s, l = U, A != null ? Ga(t, !!n, A, !1) : !!l != !!n && (e != null ? Ga(t, !!n, e, !0) : Ga(t, !!n, n ? [] : "", !1));
        return;
      case "textarea":
        U = A = null;
        for (h in n)
          if (i = n[h], n.hasOwnProperty(h) && i != null && !l.hasOwnProperty(h))
            switch (h) {
              case "value":
                break;
              case "children":
                break;
              default:
                Vt(t, e, h, null, l, i);
            }
        for (s in l)
          if (i = l[s], o = n[s], l.hasOwnProperty(s) && (i != null || o != null))
            switch (s) {
              case "value":
                i !== o && (Mt = !0), A = i;
                break;
              case "defaultValue":
                i !== o && (Mt = !0), U = i;
                break;
              case "children":
                break;
              case "dangerouslySetInnerHTML":
                if (i != null) throw Error(c(91));
                break;
              default:
                i !== o && Vt(t, e, s, i, l, o);
            }
        am(t, A, U);
        return;
      case "option":
        for (var nt in n)
          if (A = n[nt], n.hasOwnProperty(nt) && A != null && !l.hasOwnProperty(nt))
            switch (nt) {
              case "selected":
                t.selected = !1;
                break;
              default:
                Vt(
                  t,
                  e,
                  nt,
                  null,
                  l,
                  A
                );
            }
        for (T in l)
          if (A = l[T], U = n[T], l.hasOwnProperty(T) && A !== U && (A != null || U != null))
            switch (T) {
              case "selected":
                A !== U && (Mt = !0), t.selected = A && typeof A != "function" && typeof A != "symbol";
                break;
              default:
                Vt(
                  t,
                  e,
                  T,
                  A,
                  l,
                  U
                );
            }
        return;
      case "img":
      case "link":
      case "area":
      case "base":
      case "br":
      case "col":
      case "embed":
      case "hr":
      case "keygen":
      case "meta":
      case "param":
      case "source":
      case "track":
      case "wbr":
      case "menuitem":
        for (var ct in n)
          A = n[ct], n.hasOwnProperty(ct) && A != null && !l.hasOwnProperty(ct) && Vt(t, e, ct, null, l, A);
        for (z in l)
          if (A = l[z], U = n[z], l.hasOwnProperty(z) && A !== U && (A != null || U != null))
            switch (z) {
              case "children":
              case "dangerouslySetInnerHTML":
                if (A != null)
                  throw Error(c(137, e));
                break;
              default:
                Vt(
                  t,
                  e,
                  z,
                  A,
                  l,
                  U
                );
            }
        return;
      default:
        if (uc(e)) {
          for (var Ct in n)
            A = n[Ct], n.hasOwnProperty(Ct) && A !== void 0 && !l.hasOwnProperty(Ct) && of(
              t,
              e,
              Ct,
              void 0,
              l,
              A
            );
          for (j in l)
            A = l[j], U = n[j], !l.hasOwnProperty(j) || A === U || A === void 0 && U === void 0 || of(
              t,
              e,
              j,
              A,
              l,
              U
            );
          return;
        }
    }
    for (var D in n)
      A = n[D], n.hasOwnProperty(D) && A != null && !l.hasOwnProperty(D) && Vt(t, e, D, null, l, A);
    for (G in l)
      A = l[G], U = n[G], !l.hasOwnProperty(G) || A === U || A == null && U == null || Vt(t, e, G, A, l, U);
  }
  function mg(t) {
    switch (t) {
      case "css":
      case "script":
      case "font":
      case "img":
      case "image":
      case "input":
      case "link":
        return !0;
      default:
        return !1;
    }
  }
  function tS() {
    if (typeof performance.getEntriesByType == "function") {
      for (var t = 0, e = 0, n = performance.getEntriesByType("resource"), l = 0; l < n.length; l++) {
        var i = n[l], o = i.transferSize, s = i.initiatorType, h = i.duration;
        if (o && h && mg(s)) {
          for (s = 0, h = i.responseEnd, l += 1; l < n.length; l++) {
            var T = n[l], z = T.startTime;
            if (z > h) break;
            var j = T.transferSize, G = T.initiatorType;
            j && mg(G) && (T = T.responseEnd, s += j * (T < h ? 1 : (h - z) / (T - z)));
          }
          if (--l, e += 8 * (o + s) / (i.duration / 1e3), t++, 10 < t) break;
        }
      }
      if (0 < t) return e / t / 1e6;
    }
    return navigator.connection && (t = navigator.connection.downlink, typeof t == "number") ? t : 5;
  }
  var uf = null, rf = null;
  function No(t) {
    return t.nodeType === 9 ? t : t.ownerDocument;
  }
  function vg(t) {
    switch (t) {
      case "http://www.w3.org/2000/svg":
        return 1;
      case "http://www.w3.org/1998/Math/MathML":
        return 2;
      default:
        return 0;
    }
  }
  function hg(t, e) {
    if (t === 0)
      switch (e) {
        case "svg":
          return 1;
        case "math":
          return 2;
        default:
          return 0;
      }
    return t === 1 && e === "foreignObject" ? 0 : t;
  }
  function gg(t, e, n, l) {
    return n = No(
      n
    ).createElement(t), n[pe] = l, n[Be] = e, Te(n, t, e), fe(n), n;
  }
  function cf(t, e) {
    return t === "textarea" || t === "noscript" || typeof e.children == "string" || typeof e.children == "number" || typeof e.children == "bigint" || typeof e.dangerouslySetInnerHTML == "object" && e.dangerouslySetInnerHTML !== null && e.dangerouslySetInnerHTML.__html != null;
  }
  var sf = null;
  function eS() {
    var t = window.event;
    return t && t.type === "popstate" ? t === sf ? !1 : (sf = t, !0) : (sf = null, !1);
  }
  var ff = typeof setTimeout == "function" ? setTimeout : void 0, nS = typeof clearTimeout == "function" ? clearTimeout : void 0, yg = typeof Promise == "function" ? Promise : void 0, pg = typeof requestAnimationFrame == "function" ? requestAnimationFrame : ff, lS = typeof queueMicrotask == "function" ? queueMicrotask : typeof yg < "u" ? function(t) {
    return yg.resolve(null).then(t).catch(aS);
  } : ff;
  function aS(t) {
    setTimeout(function() {
      throw t;
    });
  }
  function Xl(t) {
    return t === "head";
  }
  function bg(t, e) {
    var n = e, l = 0;
    do {
      var i = n.nextSibling;
      if (t.removeChild(n), i && i.nodeType === 8)
        if (n = i.data, n === "/$" || n === "/&") {
          if (l === 0) {
            t.removeChild(i), Oi(e);
            return;
          }
          l--;
        } else if (n === "$" || n === "$?" || n === "$~" || n === "$!" || n === "&")
          l++;
        else if (n === "html")
          bf(
            t.ownerDocument.documentElement
          );
        else if (n === "head") {
          n = t.ownerDocument.head, bf(n);
          for (var o = n.firstChild; o; ) {
            var s = o.nextSibling, h = o.nodeName;
            o[Ki] || h === "SCRIPT" || h === "STYLE" || h === "LINK" && o.rel.toLowerCase() === "stylesheet" || n.removeChild(o), o = s;
          }
        } else
          n === "body" && bf(t.ownerDocument.body);
      n = i;
    } while (n);
    Oi(e);
  }
  function Sg(t, e) {
    var n = t;
    t = 0;
    do {
      var l = n.nextSibling;
      if (n.nodeType === 1 ? e ? (n._stashedDisplay = n.style.display, n.style.display = "none") : (n.style.display = n._stashedDisplay || "", n.getAttribute("style") === "" && n.removeAttribute("style")) : n.nodeType === 3 && (e ? (n._stashedText = n.nodeValue, n.nodeValue = "") : n.nodeValue = n._stashedText || ""), l && l.nodeType === 8)
        if (n = l.data, n === "/$") {
          if (t === 0) break;
          t--;
        } else
          n !== "$" && n !== "$?" && n !== "$~" && n !== "$!" || t++;
      n = l;
    } while (n);
  }
  function Eg(t, e, n) {
    if (e = CSS.escape(e) !== e ? "r-" + btoa(e).replace(/=/g, "") : e, t.style.viewTransitionName = e, n != null && (t.style.viewTransitionClass = n), n = getComputedStyle(t), n.display === "inline") {
      if (e = t.getClientRects(), e.length === 1) var l = 1;
      else
        for (var i = l = 0; i < e.length; i++) {
          var o = e[i];
          0 < o.width && 0 < o.height && l++;
        }
      l === 1 && (t = t.style, t.display = e.length === 1 ? "inline-block" : "block", t.marginTop = "-" + n.paddingTop, t.marginBottom = "-" + n.paddingBottom);
    }
  }
  function xg(t, e) {
    t = t.style, e = e.style;
    var n = e != null ? e.hasOwnProperty("viewTransitionName") ? e.viewTransitionName : e.hasOwnProperty("view-transition-name") ? e["view-transition-name"] : null : null;
    t.viewTransitionName = n == null || typeof n == "boolean" ? "" : ("" + n).trim(), n = e != null ? e.hasOwnProperty("viewTransitionClass") ? e.viewTransitionClass : e.hasOwnProperty("view-transition-class") ? e["view-transition-class"] : null : null, t.viewTransitionClass = n == null || typeof n == "boolean" ? "" : ("" + n).trim(), t.display === "inline-block" && (e == null ? t.display = t.margin = "" : (n = e.display, t.display = n == null || typeof n == "boolean" ? "" : n, n = e.margin, n != null ? t.margin = n : (n = e.hasOwnProperty("marginTop") ? e.marginTop : e["margin-top"], t.marginTop = n == null || typeof n == "boolean" ? "" : n, e = e.hasOwnProperty("marginBottom") ? e.marginBottom : e["margin-bottom"], t.marginBottom = e == null || typeof e == "boolean" ? "" : e)));
  }
  function iS(t, e, n) {
    return n = n.ownerDocument.defaultView, {
      rect: t,
      abs: e.position === "absolute" || e.position === "fixed",
      clip: e.clipPath !== "none" || e.overflow !== "visible" || e.filter !== "none" || e.mask !== "none" || e.mask !== "none" || e.borderRadius !== "0px",
      view: 0 <= t.bottom && 0 <= t.right && t.top <= n.innerHeight && t.left <= n.innerWidth
    };
  }
  function df(t) {
    var e = t.getBoundingClientRect(), n = getComputedStyle(t);
    return iS(e, n, t);
  }
  function oS(t) {
    return t.documentElement.clientHeight;
  }
  function uS(t) {
    this.addEventListener("load", t), this.addEventListener("error", t);
  }
  function rS(t, e, n, l, i, o, s, h, T) {
    var z = e.nodeType === 9 ? e : e.ownerDocument;
    try {
      var j = z.startViewTransition({
        update: function() {
          var A = z.defaultView, U = A.navigation && A.navigation.transition, nt = z.fonts.status;
          l();
          var ct = [];
          if (nt === "loaded" && (oS(z), z.fonts.status === "loading" && ct.push(z.fonts.ready)), nt = ct.length, t !== null)
            for (var Ct = t.suspenseyImages, D = 0, w = 0; w < Ct.length; w++) {
              var M = Ct[w];
              if (!M.complete) {
                var q = M.getBoundingClientRect();
                if (0 < q.bottom && 0 < q.right && q.top < A.innerHeight && q.left < A.innerWidth) {
                  if (D += Xg(M), D > yr) {
                    ct.length = nt;
                    break;
                  }
                  M = new Promise(
                    uS.bind(M)
                  ), ct.push(M);
                }
              }
            }
          if (0 < ct.length)
            return A = Promise.race([
              Promise.all(ct),
              new Promise(function(it) {
                return setTimeout(it, 500);
              })
            ]).then(i, i), (U ? Promise.allSettled([U.finished, A]) : A).then(o, o);
          if (i(), U)
            return U.finished.then(
              o,
              o
            );
          o();
        },
        types: n
      });
      z.__reactViewTransition = j;
      var G = [];
      return j.ready.then(
        function() {
          for (var A = z.documentElement.getAnimations({
            subtree: !0
          }), U = 0; U < A.length; U++) {
            var nt = A[U], ct = nt.effect, Ct = ct.pseudoElement;
            if (Ct != null && Ct.startsWith("::view-transition")) {
              G.push(nt), nt = ct.getKeyframes();
              for (var D = Ct = void 0, w = !0, M = 0; M < nt.length; M++) {
                var q = nt[M], it = q.width;
                if (Ct === void 0) Ct = it;
                else if (Ct !== it) {
                  w = !1;
                  break;
                }
                if (it = q.height, D === void 0) D = it;
                else if (D !== it) {
                  w = !1;
                  break;
                }
                delete q.width, delete q.height, q.transform === "none" && delete q.transform;
              }
              w && Ct !== void 0 && D !== void 0 && (ct.setKeyframes(nt), w = getComputedStyle(
                ct.target,
                ct.pseudoElement
              ), w.width !== Ct || w.height !== D) && (w = nt[0], w.width = Ct, w.height = D, w = nt[nt.length - 1], w.width = Ct, w.height = D, ct.setKeyframes(nt));
            }
          }
          s();
        },
        function(A) {
          z.__reactViewTransition === j && (z.__reactViewTransition = null);
          try {
            if (typeof A == "object" && A !== null)
              switch (A.name) {
                case "InvalidStateError":
                  (A.message === "View transition was skipped because document visibility state is hidden." || A.message === "Skipping view transition because document visibility state has become hidden." || A.message === "Skipping view transition because viewport size changed." || A.message === "Transition was aborted because of invalid state") && (A = null);
              }
            A !== null && T(A);
          } finally {
            l(), i(), s();
          }
        }
      ), j.finished.finally(function() {
        for (var A = 0; A < G.length; A++)
          G[A].cancel();
        z.__reactViewTransition === j && (z.__reactViewTransition = null), h();
      }), j;
    } catch {
      return l(), i(), s(), null;
    }
  }
  function Oa(t, e) {
    this._scope = document.documentElement, this._selector = "::view-transition-" + t + "(" + e + ")";
  }
  Oa.prototype.animate = function(t, e) {
    return e = typeof e == "number" ? { duration: e } : X({}, e), e.pseudoElement = this._selector, this._scope.animate(t, e);
  }, Oa.prototype.getAnimations = function() {
    for (var t = this._scope, e = this._selector, n = t.getAnimations({ subtree: !0 }), l = [], i = 0; i < n.length; i++) {
      var o = n[i].effect;
      o !== null && o.target === t && o.pseudoElement === e && l.push(n[i]);
    }
    return l;
  }, Oa.prototype.getComputedStyle = function() {
    return getComputedStyle(this._scope, this._selector);
  };
  function Tg(t) {
    return {
      name: t,
      group: new Oa("group", t),
      imagePair: new Oa("image-pair", t),
      old: new Oa("old", t),
      new: new Oa("new", t)
    };
  }
  function nn(t) {
    this._fragmentFiber = t, this._observers = this._eventListeners = null;
  }
  nn.prototype.addEventListener = function(t, e, n) {
    var l = null, i = null;
    if (!(n != null && typeof n != "boolean" && (l = n.signal || null, l !== null && l.aborted))) {
      this._eventListeners === null && (this._eventListeners = []);
      var o = this._eventListeners;
      if (Cg(o, t, e, n) === -1) {
        var s = this, h = e;
        n != null && typeof n != "boolean" && n.once === !0 && (h = function(T) {
          s.removeEventListener(
            t,
            e,
            n
          ), typeof e == "function" ? e.call(this, T) : e.handleEvent(T);
        }), l !== null && (i = s.removeEventListener.bind(
          s,
          t,
          e,
          n
        ), l.addEventListener("abort", i, { once: !0 }), i = l.removeEventListener.bind(l, "abort", i)), l = Si(n), o.push({
          type: t,
          listener: e,
          optionsOrUseCapture: n,
          attachedListener: h,
          cleanup: i
        }), d(
          this._fragmentFiber.child,
          !1,
          cS,
          t,
          h,
          l
        );
      }
      this._eventListeners = o;
    }
  };
  function cS(t, e, n, l) {
    return N(t).addEventListener(
      e,
      n,
      l
    ), !1;
  }
  nn.prototype.removeEventListener = function(t, e, n) {
    var l = this._eventListeners;
    if (l !== null && (e = Cg(
      l,
      t,
      e,
      n
    ), e !== -1)) {
      var i = l[e];
      n = i.attachedListener;
      var o = i.cleanup;
      i = Si(i.optionsOrUseCapture), d(
        this._fragmentFiber.child,
        !1,
        sS,
        t,
        n,
        i
      ), l.splice(e, 1), o !== null && o();
    }
  };
  function sS(t, e, n, l) {
    return N(t).removeEventListener(
      e,
      n,
      l
    ), !1;
  }
  function Si(t) {
    return t != null && typeof t != "boolean" && (t.once === !0 || t.signal instanceof AbortSignal) ? { capture: t.capture, passive: t.passive } : t;
  }
  function wg(t) {
    return t == null ? "c=0" : typeof t == "boolean" ? "c=" + (t ? "1" : "0") : "c=" + (t.capture ? "1" : "0");
  }
  function Cg(t, e, n, l) {
    if (t.length === 0) return -1;
    l = wg(l);
    for (var i = 0; i < t.length; i++) {
      var o = t[i];
      if (o.type === e && o.listener === n && wg(o.optionsOrUseCapture) === l)
        return i;
    }
    return -1;
  }
  nn.prototype.dispatchEvent = function(t) {
    var e = x(
      this._fragmentFiber
    );
    if (e === null) return !0;
    e = N(e);
    var n = this._eventListeners;
    if (n !== null && 0 < n.length || !t.bubbles) {
      var l = e.nodeType === 9 ? e.createComment("") : document.createTextNode("");
      if (n)
        for (var i = 0; i < n.length; i++) {
          var o = n[i];
          l.addEventListener(
            o.type,
            o.attachedListener,
            Si(o.optionsOrUseCapture)
          );
        }
      if (e.appendChild(l), t = l.dispatchEvent(t), n)
        for (i = 0; i < n.length; i++)
          o = n[i], l.removeEventListener(
            o.type,
            o.attachedListener,
            Si(o.optionsOrUseCapture)
          );
      return e.removeChild(l), t;
    }
    return e.dispatchEvent(t);
  }, nn.prototype.focus = function(t) {
    d(
      this._fragmentFiber.child,
      !0,
      Og,
      t,
      void 0,
      void 0
    );
  };
  function Og(t, e) {
    return t.tag === 6 ? !1 : (t = N(t), xS(t, e));
  }
  nn.prototype.focusLast = function(t) {
    var e = [];
    d(
      this._fragmentFiber.child,
      !0,
      mf,
      e,
      void 0,
      void 0
    );
    for (var n = e.length - 1; 0 <= n && !Og(e[n], t); n--) ;
  };
  function mf(t, e) {
    return e.push(t), !1;
  }
  nn.prototype.blur = function() {
    var t = x(
      this._fragmentFiber
    );
    t !== null && (t = N(t), t = No(t).activeElement, t !== null && d(
      this._fragmentFiber.child,
      !1,
      fS,
      t,
      void 0,
      void 0
    ));
  };
  function fS(t, e) {
    return t.tag === 6 ? !1 : (t = N(t), t === e || t.contains(e) ? (e.blur(), !0) : !1);
  }
  nn.prototype.observeUsing = function(t) {
    this._observers === null && (this._observers = /* @__PURE__ */ new Set()), this._observers.add(t), d(
      this._fragmentFiber.child,
      !1,
      dS,
      t,
      void 0,
      void 0
    );
  };
  function dS(t, e) {
    return t.tag === 6 || (t = N(t), e.observe(t)), !1;
  }
  nn.prototype.unobserveUsing = function(t) {
    var e = this._observers;
    if (e !== null && e.has(t)) {
      e.delete(t), d(
        this._fragmentFiber.child,
        !1,
        mS,
        t,
        void 0,
        void 0
      );
      for (var n = e = 0; n < _n.length; n++) {
        var l = _n[n];
        l.fragmentInstance === this && l.observer === t ? t.unobserve(l.instance) : _n[e++] = l;
      }
      _n.length = e;
    }
  };
  function mS(t, e) {
    return t.tag === 6 || (t = N(t), e.unobserve(t)), !1;
  }
  var _n = [], vf = !1;
  function vS(t, e, n) {
    _n.push({
      fragmentInstance: t,
      observer: e,
      instance: n
    }), vf || (vf = !0, TS(function() {
      vf = !1;
      var l = _n;
      _n = [];
      for (var i = 0; i < l.length; i++) {
        var o = l[i];
        o.observer.unobserve(o.instance);
      }
    }));
  }
  nn.prototype.getClientRects = function() {
    var t = [];
    return d(
      this._fragmentFiber.child,
      !1,
      hS,
      t,
      void 0,
      void 0
    ), t;
  };
  function hS(t, e) {
    if (t.tag === 6) {
      t = t.stateNode;
      var n = t.ownerDocument.createRange();
      n.selectNodeContents(t), e.push.apply(e, n.getClientRects());
    } else
      t = N(t), e.push.apply(e, t.getClientRects());
    return !1;
  }
  nn.prototype.getRootNode = function(t) {
    var e = x(
      this._fragmentFiber
    );
    return e === null ? this : N(e).getRootNode(t);
  }, nn.prototype.compareDocumentPosition = function(t) {
    var e = x(
      this._fragmentFiber
    );
    if (e === null) return Node.DOCUMENT_POSITION_DISCONNECTED;
    var n = [];
    d(
      this._fragmentFiber.child,
      !1,
      mf,
      n,
      void 0,
      void 0
    );
    var l = N(e);
    if (n.length === 0) {
      if (n = l, C(this._fragmentFiber)) {
        t: {
          for (e = this._fragmentFiber.return; e !== null; ) {
            if (e.tag === 4) {
              e = e.stateNode.containerInfo;
              break t;
            }
            if (e.tag === 3 || e.tag === 5 || e.tag === 27)
              break;
            e = e.return;
          }
          e = null;
        }
        e != null && (n = e);
      }
      e = this._fragmentFiber;
      var i = l = n.compareDocumentPosition(t);
      return n === t ? i = Node.DOCUMENT_POSITION_CONTAINS : l & Node.DOCUMENT_POSITION_CONTAINED_BY && (n = R(e)[1], n === null ? i = Node.DOCUMENT_POSITION_PRECEDING : (t = N(n).compareDocumentPosition(
        t
      ), i = t === 0 || t & Node.DOCUMENT_POSITION_FOLLOWING ? Node.DOCUMENT_POSITION_FOLLOWING : Node.DOCUMENT_POSITION_PRECEDING)), i |= Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC;
    }
    e = N(n[0]), i = N(n[n.length - 1]);
    var o = C(this._fragmentFiber) ? e.parentElement : l;
    if (o == null)
      return Node.DOCUMENT_POSITION_DISCONNECTED;
    l = o.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_CONTAINED_BY, o = o.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_CONTAINED_BY;
    var s = e.compareDocumentPosition(t), h = i.compareDocumentPosition(t), T = s & Node.DOCUMENT_POSITION_CONTAINED_BY || h & Node.DOCUMENT_POSITION_CONTAINED_BY;
    return h = l && o && s & Node.DOCUMENT_POSITION_FOLLOWING && h & Node.DOCUMENT_POSITION_PRECEDING, e = l && e === t || o && i === t || T || h ? Node.DOCUMENT_POSITION_CONTAINED_BY : !l && e === t || !o && i === t ? Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC : s, e & Node.DOCUMENT_POSITION_DISCONNECTED || e & Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC || gS(
      e,
      this._fragmentFiber,
      n[0],
      n[n.length - 1],
      t
    ) ? e : Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC;
  };
  function gS(t, e, n, l, i) {
    var o = ia(i);
    if (t & Node.DOCUMENT_POSITION_CONTAINED_BY) {
      if (n = !!o)
        t: {
          for (; o !== null; ) {
            if (o.tag === 7 && (o === e || o.alternate === e)) {
              n = !0;
              break t;
            }
            o = o.return;
          }
          n = !1;
        }
      return n;
    }
    if (t & Node.DOCUMENT_POSITION_CONTAINS) {
      if (o === null)
        return o = i.ownerDocument, i === o || i === o.documentElement || i === o.body;
      t: {
        for (o = e, e = x(e); o !== null; ) {
          if (!(o.tag !== 5 && o.tag !== 3 && o.tag !== 27 || o !== e && o.alternate !== e)) {
            o = !0;
            break t;
          }
          o = o.return;
        }
        o = !1;
      }
      return o;
    }
    return t & Node.DOCUMENT_POSITION_PRECEDING ? ((e = !!o) && !(e = o === n) && (e = Z(
      n,
      o,
      I
    ), e === null ? e = !1 : (d(
      e,
      !0,
      J,
      o,
      n
    ), o = H, H = null, e = o !== null)), e) : t & Node.DOCUMENT_POSITION_FOLLOWING ? ((e = !!o) && !(e = o === l) && (e = Z(
      l,
      o,
      I
    ), e === null ? e = !1 : (d(
      e,
      !0,
      K,
      o,
      l
    ), o = H, L = H = null, e = o !== null)), e) : !1;
  }
  function _g(t, e) {
    var n = t.ownerDocument.createRange();
    n.selectNodeContents(t), t = n.getBoundingClientRect(), window.scrollTo(
      window.scrollX + t.left,
      e ? window.scrollY + t.top : window.scrollY + t.bottom - window.innerHeight
    );
  }
  nn.prototype.scrollIntoView = function(t) {
    if (typeof t == "object") throw Error(c(566));
    var e = [];
    d(
      this._fragmentFiber.child,
      !1,
      mf,
      e,
      void 0,
      void 0
    );
    var n = t !== !1;
    if (e.length === 0) {
      var l = R(
        this._fragmentFiber
      );
      if (l = n ? l[1] || l[0] || x(this._fragmentFiber) : l[0] || l[1], l === null) return;
      if (l.tag === 6) {
        t = N(l), _g(t, n);
        return;
      }
      if (l = N(l), l.nodeType !== 9) {
        if (l.nodeType === 11) {
          n = "host" in l ? l.host : null, n !== null && n.scrollIntoView(t);
          return;
        }
        l.scrollIntoView(t);
      }
    }
    for (l = n ? e.length - 1 : 0; l !== (n ? -1 : e.length); ) {
      var i = e[l];
      i.tag === 6 ? (i = N(i), _g(i, n)) : N(i).scrollIntoView(t), l += n ? -1 : 1;
    }
  };
  function yS(t, e) {
    return t = N(t), Ag(t, e), !1;
  }
  function Ag(t, e) {
    t.reactFragments == null && (t.reactFragments = /* @__PURE__ */ new Set()), t.reactFragments.add(e);
  }
  function Rg(t, e) {
    var n = e._eventListeners;
    if (n !== null)
      for (var l = 0; l < n.length; l++) {
        var i = n[l];
        t.addEventListener(
          i.type,
          i.attachedListener,
          Si(i.optionsOrUseCapture)
        );
      }
    t.nodeType !== 3 && (n = e._observers, n !== null && n.forEach(function(o) {
      for (var s = 0, h = 0; h < _n.length; h++) {
        var T = _n[h];
        (T.fragmentInstance !== e || T.observer !== o || T.instance !== t) && (_n[s++] = T);
      }
      _n.length = s, o.observe(t);
    }), Ag(t, e));
  }
  function pS(t, e) {
    var n = e._eventListeners;
    if (n !== null)
      for (var l = 0; l < n.length; l++) {
        var i = n[l];
        t.removeEventListener(
          i.type,
          i.attachedListener,
          Si(i.optionsOrUseCapture)
        );
      }
    t.nodeType !== 3 && (n = e._observers, n !== null && n.forEach(function(o) {
      typeof o.rootMargin == "string" ? vS(
        e,
        o,
        t
      ) : o.unobserve(t);
    }), t.reactFragments != null && t.reactFragments.delete(e));
  }
  function hf(t) {
    var e = t.firstChild;
    for (e && e.nodeType === 10 && (e = e.nextSibling); e; ) {
      var n = e;
      switch (e = e.nextSibling, n.nodeName) {
        case "HTML":
        case "HEAD":
        case "BODY":
          hf(n), iu(n);
          continue;
        case "SCRIPT":
        case "STYLE":
          continue;
        case "LINK":
          if (n.rel.toLowerCase() === "stylesheet") continue;
      }
      t.removeChild(n);
    }
  }
  function bS(t, e, n, l) {
    for (; t.nodeType === 1; ) {
      var i = n;
      if (t.nodeName.toLowerCase() !== e.toLowerCase()) {
        if (!l && (t.nodeName !== "INPUT" || t.type !== "hidden"))
          break;
      } else if (l) {
        if (!t[Ki])
          switch (e) {
            case "meta":
              if (!t.hasAttribute("itemprop")) break;
              return t;
            case "link":
              if (o = t.getAttribute("rel"), o === "stylesheet" && t.hasAttribute("data-precedence"))
                break;
              if (o !== i.rel || t.getAttribute("href") !== (i.href == null || i.href === "" ? null : i.href) || t.getAttribute("crossorigin") !== (i.crossOrigin == null ? null : i.crossOrigin) || t.getAttribute("title") !== (i.title == null ? null : i.title))
                break;
              return t;
            case "style":
              if (t.hasAttribute("data-precedence")) break;
              return t;
            case "script":
              if (o = t.getAttribute("src"), (o !== (i.src == null ? null : i.src) || t.getAttribute("type") !== (i.type == null ? null : i.type) || t.getAttribute("crossorigin") !== (i.crossOrigin == null ? null : i.crossOrigin)) && o && t.hasAttribute("async") && !t.hasAttribute("itemprop"))
                break;
              return t;
            default:
              return t;
          }
      } else if (e === "input" && t.type === "hidden") {
        var o = i.name == null ? null : "" + i.name;
        if (i.type === "hidden" && t.getAttribute("name") === o)
          return t;
      } else return t;
      if (t = hn(t.nextSibling), t === null) break;
    }
    return null;
  }
  function SS(t, e, n) {
    if (e === "") return null;
    for (; t.nodeType !== 3; )
      if ((t.nodeType !== 1 || t.nodeName !== "INPUT" || t.type !== "hidden") && !n || (t = hn(t.nextSibling), t === null)) return null;
    return t;
  }
  function Ng(t, e) {
    for (; t.nodeType !== 8; )
      if ((t.nodeType !== 1 || t.nodeName !== "INPUT" || t.type !== "hidden") && !e || (t = hn(t.nextSibling), t === null)) return null;
    return t;
  }
  function gf(t) {
    return t.data === "$?" || t.data === "$~";
  }
  function yf(t) {
    return t.data === "$!" || t.data === "$?" && t.ownerDocument.readyState !== "loading";
  }
  function ES(t, e) {
    var n = t.ownerDocument;
    if (t.data === "$~") t._reactRetry = e;
    else if (t.data !== "$?" || n.readyState !== "loading")
      e();
    else {
      var l = function() {
        e(), n.removeEventListener("DOMContentLoaded", l);
      };
      n.addEventListener("DOMContentLoaded", l), t._reactRetry = l;
    }
  }
  function hn(t) {
    for (; t != null; t = t.nextSibling) {
      var e = t.nodeType;
      if (e === 1 || e === 3) break;
      if (e === 8) {
        if (e = t.data, e === "$" || e === "$!" || e === "$?" || e === "$~" || e === "&" || e === "F!" || e === "F")
          break;
        if (e === "/$" || e === "/&") return null;
      }
    }
    return t;
  }
  var pf = null;
  function Dg(t) {
    t = t.nextSibling;
    for (var e = 0; t; ) {
      if (t.nodeType === 8) {
        var n = t.data;
        if (n === "/$" || n === "/&") {
          if (e === 0)
            return hn(t.nextSibling);
          e--;
        } else
          n !== "$" && n !== "$!" && n !== "$?" && n !== "$~" && n !== "&" || e++;
      }
      t = t.nextSibling;
    }
    return null;
  }
  function zg(t) {
    t = t.previousSibling;
    for (var e = 0; t; ) {
      if (t.nodeType === 8) {
        var n = t.data;
        if (n === "$" || n === "$!" || n === "$?" || n === "$~" || n === "&") {
          if (e === 0) return t;
          e--;
        } else n !== "/$" && n !== "/&" || e++;
      }
      t = t.previousSibling;
    }
    return null;
  }
  function xS(t, e) {
    function n() {
      l = !0;
    }
    if (t.ownerDocument.activeElement === t) return !0;
    var l = !1;
    try {
      t.ownerDocument.addEventListener("focus", n, !0), (t.focus || HTMLElement.prototype.focus).call(t, e);
    } finally {
      t.ownerDocument.removeEventListener("focus", n, !0);
    }
    return l;
  }
  function TS(t) {
    pg(function() {
      pg(function(e) {
        return t(e);
      });
    });
  }
  function Mg(t, e, n) {
    switch (e = No(n), t) {
      case "html":
        if (t = e.documentElement, !t) throw Error(c(452));
        return t;
      case "head":
        if (t = e.head, !t) throw Error(c(453));
        return t;
      case "body":
        if (t = e.body, !t) throw Error(c(454));
        return t;
      default:
        throw Error(c(451));
    }
  }
  function Ug(t, e, n) {
    for (var l in n) {
      var i = n[l];
      n.hasOwnProperty(l) && i != null && Vt(t, e, l, null, P1, i);
    }
    n.dangerouslySetInnerHTML != null && (t.textContent = ""), t.onclick === Dn && (t.onclick = null), iu(t);
  }
  function bf(t) {
    for (var e = t.attributes; e.length; )
      t.removeAttributeNode(e[0]);
    iu(t);
  }
  var gn = /* @__PURE__ */ new Map(), Hg = /* @__PURE__ */ new Set();
  function Do(t) {
    if (typeof t.getRootNode == "function") {
      var e = t.getRootNode();
      if (e.nodeType === 9 || e.nodeType === 11) return e;
    }
    return t.nodeType === 9 ? t : t.ownerDocument;
  }
  var ml = mt.d;
  mt.d = {
    f: wS,
    r: CS,
    D: OS,
    C: _S,
    L: AS,
    m: RS,
    X: DS,
    S: NS,
    M: zS
  };
  function wS() {
    var t = ml.f(), e = rr();
    return t || e;
  }
  function CS(t) {
    var e = Ya(t);
    e !== null && e.tag === 5 && e.type === "form" ? Bv(e) : ml.r(t);
  }
  var Ei = typeof document > "u" ? null : document;
  function jg(t, e, n) {
    var l = Ei;
    if (l && typeof e == "string" && e) {
      var i = rn(e);
      i = 'link[rel="' + t + '"][href="' + i + '"]', typeof n == "string" && (i += '[crossorigin="' + n + '"]'), Hg.has(i) || (Hg.add(i), t = { rel: t, crossOrigin: n, href: e }, l.querySelector(i) === null && (e = l.createElement("link"), Te(e, "link", t), fe(e), l.head.appendChild(e)));
    }
  }
  function OS(t) {
    ml.D(t), jg("dns-prefetch", t, null);
  }
  function _S(t, e) {
    ml.C(t, e), jg("preconnect", t, e);
  }
  function AS(t, e, n) {
    ml.L(t, e, n);
    var l = Ei;
    if (l && t && e) {
      var i = 'link[rel="preload"][as="' + rn(e) + '"]';
      e === "image" && n && n.imageSrcSet ? (i += '[imagesrcset="' + rn(
        n.imageSrcSet
      ) + '"]', typeof n.imageSizes == "string" && (i += '[imagesizes="' + rn(
        n.imageSizes
      ) + '"]')) : i += '[href="' + rn(t) + '"]';
      var o = i;
      switch (e) {
        case "style":
          o = xi(t);
          break;
        case "script":
          o = Ti(t);
      }
      if (!(gn.has(o) || (t = X(
        {
          rel: "preload",
          href: e === "image" && n && n.imageSrcSet ? void 0 : t,
          as: e
        },
        n
      ), gn.set(o, t), l.querySelector(i) !== null || e === "style" && l.querySelector(zo(o)) || e === "script" && l.querySelector(Mo(o))))) {
        var s = l.createElement("link");
        Te(s, "link", t), e === "style" && (s[au] = !0, s.onload = s.onerror = function() {
          Fd(s);
        }), fe(s), l.head.appendChild(s);
      }
    }
  }
  function RS(t, e) {
    ml.m(t, e);
    var n = Ei;
    if (n && t) {
      var l = e && typeof e.as == "string" ? e.as : "script", i = 'link[rel="modulepreload"][as="' + rn(l) + '"][href="' + rn(t) + '"]', o = i;
      switch (l) {
        case "audioworklet":
        case "paintworklet":
        case "serviceworker":
        case "sharedworker":
        case "worker":
        case "script":
          o = Ti(t);
      }
      if (!gn.has(o) && (t = X({ rel: "modulepreload", href: t }, e), gn.set(o, t), n.querySelector(i) === null)) {
        switch (l) {
          case "audioworklet":
          case "paintworklet":
          case "serviceworker":
          case "sharedworker":
          case "worker":
          case "script":
            if (n.querySelector(Mo(o)))
              return;
        }
        l = n.createElement("link"), Te(l, "link", t), fe(l), n.head.appendChild(l);
      }
    }
  }
  function NS(t, e, n) {
    ml.S(t, e, n);
    var l = Ei;
    if (l && t) {
      var i = qa(l).hoistableStyles, o = xi(t);
      e = e || "default";
      var s = i.get(o);
      if (!s) {
        var h = { loading: 0, preload: null };
        if (s = l.querySelector(
          zo(o)
        ))
          h.loading = 5;
        else {
          t = X(
            { rel: "stylesheet", href: t, "data-precedence": e },
            n
          ), (n = gn.get(o)) && Sf(t, n);
          var T = s = l.createElement("link");
          fe(T), Te(T, "link", t), T._p = new Promise(function(z, j) {
            T.onload = z, T.onerror = j;
          }), T.addEventListener("load", function() {
            h.loading |= 1;
          }), T.addEventListener("error", function() {
            h.loading |= 2;
          }), h.loading |= 4, hr(s, e, l);
        }
        s = {
          type: "stylesheet",
          instance: s,
          count: 1,
          state: h
        }, i.set(o, s);
      }
    }
  }
  function DS(t, e) {
    ml.X(t, e);
    var n = Ei;
    if (n && t) {
      var l = qa(n).hoistableScripts, i = Ti(t), o = l.get(i);
      o || (o = n.querySelector(Mo(i)), o || (t = X({ src: t, async: !0 }, e), (e = gn.get(i)) && Ef(t, e), o = n.createElement("script"), fe(o), Te(o, "link", t), n.head.appendChild(o)), o = {
        type: "script",
        instance: o,
        count: 1,
        state: null
      }, l.set(i, o));
    }
  }
  function zS(t, e) {
    ml.M(t, e);
    var n = Ei;
    if (n && t) {
      var l = qa(n).hoistableScripts, i = Ti(t), o = l.get(i);
      o || (o = n.querySelector(Mo(i)), o || (t = X({ src: t, async: !0, type: "module" }, e), (e = gn.get(i)) && Ef(t, e), o = n.createElement("script"), fe(o), Te(o, "link", t), n.head.appendChild(o)), o = {
        type: "script",
        instance: o,
        count: 1,
        state: null
      }, l.set(i, o));
    }
  }
  function Bg(t, e, n, l) {
    var i = (i = an.current) ? Do(i) : null;
    if (!i) throw Error(c(446));
    switch (t) {
      case "meta":
      case "title":
        return null;
      case "style":
        return typeof n.precedence == "string" && typeof n.href == "string" ? (n = xi(n.href), e = qa(
          i
        ).hoistableStyles, l = e.get(n), l || (l = {
          type: "style",
          instance: null,
          count: 0,
          state: null
        }, e.set(n, l)), l) : { type: "void", instance: null, count: 0, state: null };
      case "link":
        if (n.rel === "stylesheet" && typeof n.href == "string" && typeof n.precedence == "string") {
          t = xi(n.href);
          var o = qa(
            i
          ).hoistableStyles, s = o.get(t);
          if (s || (i = i.ownerDocument || i, s = {
            type: "stylesheet",
            instance: null,
            count: 0,
            state: { loading: 0, preload: null }
          }, o.set(t, s), (o = i.querySelector(
            zo(t)
          )) ? o._p || (s.instance = o, s.state.loading = 5) : (o = gn.get(t), o || (o = {
            rel: "preload",
            as: "style",
            href: n.href,
            crossOrigin: n.crossOrigin,
            integrity: n.integrity,
            media: n.media,
            hrefLang: n.hrefLang,
            referrerPolicy: n.referrerPolicy
          }, gn.set(t, o)), MS(
            i,
            t,
            o,
            s.state
          ))), e && l === null)
            throw Error(c(528, ""));
          return s;
        }
        if (e && l !== null)
          throw Error(c(529, ""));
        return null;
      case "script":
        return e = n.async, n = n.src, typeof n == "string" && e && typeof e != "function" && typeof e != "symbol" ? (n = Ti(n), e = qa(
          i
        ).hoistableScripts, l = e.get(n), l || (l = {
          type: "script",
          instance: null,
          count: 0,
          state: null
        }, e.set(n, l)), l) : { type: "void", instance: null, count: 0, state: null };
      default:
        throw Error(c(444, t));
    }
  }
  function xi(t) {
    return 'href="' + rn(t) + '"';
  }
  function zo(t) {
    return 'link[rel="stylesheet"][' + t + "]";
  }
  function Lg(t) {
    return X({}, t, {
      "data-precedence": t.precedence,
      precedence: null
    });
  }
  function MS(t, e, n, l) {
    if (e = t.querySelector(
      'link[rel="preload"][as="style"][' + e + "]"
    )) {
      if (e[au] !== !0) {
        l.loading = 1;
        return;
      }
    } else
      e = t.createElement("link"), e[au] = !0, e.onload = e.onerror = Fd.bind(null, e), Te(e, "link", n), fe(e), t.head.appendChild(e);
    l.preload = e, e.addEventListener("load", function() {
      return l.loading |= 1;
    }), e.addEventListener("error", function() {
      return l.loading |= 2;
    });
  }
  function Ti(t) {
    return '[src="' + rn(t) + '"]';
  }
  function Mo(t) {
    return "script[async]" + t;
  }
  function Yg(t, e, n) {
    if (e.count++, e.instance === null)
      switch (e.type) {
        case "style":
          var l = t.querySelector(
            'style[data-href~="' + rn(n.href) + '"]'
          );
          if (l)
            return e.instance = l, fe(l), l;
          var i = X({}, n, {
            "data-href": n.href,
            "data-precedence": n.precedence,
            href: null,
            precedence: null
          });
          return l = (t.ownerDocument || t).createElement(
            "style"
          ), fe(l), Te(l, "style", i), hr(l, n.precedence, t), e.instance = l;
        case "stylesheet":
          i = xi(n.href);
          var o = t.querySelector(
            zo(i)
          );
          if (o)
            return e.state.loading |= 4, e.instance = o, fe(o), o;
          l = Lg(n), (i = gn.get(i)) && Sf(l, i), o = (t.ownerDocument || t).createElement("link"), fe(o);
          var s = o;
          return s._p = new Promise(function(h, T) {
            s.onload = h, s.onerror = T;
          }), Te(o, "link", l), e.state.loading |= 4, hr(o, n.precedence, t), e.instance = o;
        case "script":
          return o = Ti(n.src), (i = t.querySelector(
            Mo(o)
          )) ? (e.instance = i, fe(i), i) : (l = n, (i = gn.get(o)) && (l = X({}, n), Ef(l, i)), t = t.ownerDocument || t, i = t.createElement("script"), fe(i), Te(i, "link", l), t.head.appendChild(i), e.instance = i);
        case "void":
          return null;
        default:
          throw Error(c(443, e.type));
      }
    else
      e.type === "stylesheet" && (e.state.loading & 4) === 0 && (l = e.instance, e.state.loading |= 4, hr(l, n.precedence, t));
    return e.instance;
  }
  function hr(t, e, n) {
    for (var l = n.querySelectorAll(
      'link[rel="stylesheet"][data-precedence],style[data-precedence]'
    ), i = l.length ? l[l.length - 1] : null, o = i, s = 0; s < l.length; s++) {
      var h = l[s];
      if (h.dataset.precedence === e) o = h;
      else if (o !== i) break;
    }
    o ? o.parentNode.insertBefore(t, o.nextSibling) : (e = n.nodeType === 9 ? n.head : n, e.insertBefore(t, e.firstChild));
  }
  function Sf(t, e) {
    t.crossOrigin == null && (t.crossOrigin = e.crossOrigin), t.referrerPolicy == null && (t.referrerPolicy = e.referrerPolicy), t.title == null && (t.title = e.title);
  }
  function Ef(t, e) {
    t.crossOrigin == null && (t.crossOrigin = e.crossOrigin), t.referrerPolicy == null && (t.referrerPolicy = e.referrerPolicy), t.integrity == null && (t.integrity = e.integrity);
  }
  var gr = null;
  function qg(t, e, n) {
    if (gr === null) {
      var l = /* @__PURE__ */ new Map(), i = gr = /* @__PURE__ */ new Map();
      i.set(n, l);
    } else
      i = gr, l = i.get(n), l || (l = /* @__PURE__ */ new Map(), i.set(n, l));
    if (l.has(t)) return l;
    for (l.set(t, null), n = n.getElementsByTagName(t), i = 0; i < n.length; i++) {
      var o = n[i];
      if (!(o[Ki] || o[pe] || t === "link" && o.getAttribute("rel") === "stylesheet") && o.namespaceURI !== "http://www.w3.org/2000/svg") {
        var s = o.getAttribute(e) || "";
        s = t + s;
        var h = l.get(s);
        h ? h.push(o) : l.set(s, [o]);
      }
    }
    return l;
  }
  function xf(t, e, n) {
    t = t.ownerDocument || t, t.head.insertBefore(
      n,
      e === "title" ? t.querySelector("head > title") : null
    );
  }
  function US(t, e, n) {
    if (n === 1 || e.itemProp != null) return !1;
    switch (t) {
      case "meta":
      case "title":
        return !0;
      case "style":
        if (typeof e.precedence != "string" || typeof e.href != "string" || e.href === "")
          break;
        return !0;
      case "link":
        if (typeof e.rel != "string" || typeof e.href != "string" || e.href === "" || e.onLoad || e.onError)
          break;
        switch (e.rel) {
          case "stylesheet":
            return t = e.disabled, typeof e.precedence == "string" && t == null;
          default:
            return !0;
        }
      case "script":
        if (e.async && typeof e.async != "function" && typeof e.async != "symbol" && !e.onLoad && !e.onError && e.src && typeof e.src == "string")
          return !0;
    }
    return !1;
  }
  function Vg(t, e) {
    return t === "img" && e.src != null && e.src !== "" && e.onLoad == null && e.loading !== "lazy";
  }
  function Gg(t) {
    return !(t.type === "stylesheet" && (t.state.loading & 3) === 0);
  }
  function Xg(t) {
    return (t.width || 100) * (t.height || 100) * (typeof devicePixelRatio == "number" ? devicePixelRatio : 1) * 0.25;
  }
  function kg(t, e) {
    typeof e.decode == "function" && (t.imgCount++, e.complete || (t.imgBytes += Xg(e), t.suspenseyImages.push(e)), t = BS.bind(t), e.decode().then(t, t));
  }
  function HS(t, e, n, l) {
    if (n.type === "stylesheet" && (typeof l.media != "string" || matchMedia(l.media).matches !== !1) && (n.state.loading & 4) === 0) {
      if (n.instance === null) {
        var i = xi(l.href), o = e.querySelector(
          zo(i)
        );
        if (o) {
          e = o._p, e !== null && typeof e == "object" && typeof e.then == "function" && (t.count++, t = Uo.bind(t), e.then(t, t)), n.state.loading |= 4, n.instance = o, fe(o);
          return;
        }
        o = e.ownerDocument || e, l = Lg(l), (i = gn.get(i)) && Sf(l, i), o = o.createElement("link"), fe(o);
        var s = o;
        s._p = new Promise(function(h, T) {
          s.onload = h, s.onerror = T;
        }), Te(o, "link", l), n.instance = o;
      }
      t.stylesheets === null && (t.stylesheets = /* @__PURE__ */ new Map()), t.stylesheets.set(n, e), (e = n.state.preload) && (n.state.loading & 3) === 0 && (t.count++, n = Uo.bind(t), e.addEventListener("load", n), e.addEventListener("error", n));
    }
  }
  var yr = 0;
  function jS(t, e) {
    return t.stylesheets && t.count === 0 && br(t, t.stylesheets), 0 < t.count || 0 < t.imgCount ? function(n) {
      var l = setTimeout(function() {
        if (t.stylesheets && br(t, t.stylesheets), t.unsuspend) {
          var o = t.unsuspend;
          t.unsuspend = null, o();
        }
      }, 6e4 + e);
      0 < t.imgBytes && yr === 0 && (yr = 62500 * tS());
      var i = setTimeout(
        function() {
          if (t.waitingForImages = !1, t.count === 0 && (t.stylesheets && br(t, t.stylesheets), t.unsuspend)) {
            var o = t.unsuspend;
            t.unsuspend = null, o();
          }
        },
        (t.imgBytes > yr ? 50 : 800) + e
      );
      return t.unsuspend = n, function() {
        t.unsuspend = null, clearTimeout(l), clearTimeout(i);
      };
    } : null;
  }
  function Qg(t) {
    if (t.count === 0 && (t.imgCount === 0 || !t.waitingForImages)) {
      if (t.stylesheets) br(t, t.stylesheets);
      else if (t.unsuspend) {
        var e = t.unsuspend;
        t.unsuspend = null, e();
      }
    }
  }
  function Uo() {
    this.count--, Qg(this);
  }
  function BS() {
    this.imgCount--, Qg(this);
  }
  var pr = null;
  function br(t, e) {
    t.stylesheets = null, t.unsuspend !== null && (t.count++, pr = /* @__PURE__ */ new Map(), e.forEach(LS, t), pr = null, Uo.call(t));
  }
  function LS(t, e) {
    if (!(e.state.loading & 4)) {
      var n = pr.get(t);
      if (n) var l = n.get(null);
      else {
        n = /* @__PURE__ */ new Map(), pr.set(t, n);
        for (var i = t.querySelectorAll(
          "link[data-precedence],style[data-precedence]"
        ), o = 0; o < i.length; o++) {
          var s = i[o];
          (s.nodeName === "LINK" || s.getAttribute("media") !== "not all") && (n.set(s.dataset.precedence, s), l = s);
        }
        l && n.set(null, l);
      }
      i = e.instance, s = i.getAttribute("data-precedence"), o = n.get(s) || l, o === l && n.set(null, i), n.set(s, i), this.count++, l = Uo.bind(this), i.addEventListener("load", l), i.addEventListener("error", l), o ? o.parentNode.insertBefore(i, o.nextSibling) : (t = t.nodeType === 9 ? t.head : t, t.insertBefore(i, t.firstChild)), e.state.loading |= 4;
    }
  }
  var wi = {
    $$typeof: yt,
    Provider: null,
    Consumer: null,
    _currentValue: It,
    _currentValue2: It,
    _threadCount: 0
  };
  function YS(t, e, n, l, i, o, s, h, T) {
    this.tag = 1, this.containerInfo = t, this.pingCache = this.current = this.pendingChildren = null, this.timeoutHandle = -1, this.callbackNode = this.next = this.pendingContext = this.context = this.cancelPendingCommit = null, this.callbackPriority = 0, this.expirationTimes = ec(-1), this.entangledLanes = this.shellSuspendCounter = this.errorRecoveryDisabledLanes = this.expiredLanes = this.warmLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0, this.entanglements = ec(0), this.hiddenUpdates = ec(null), this.identifierPrefix = l, this.onUncaughtError = i, this.onCaughtError = o, this.onRecoverableError = s, this.pooledCache = null, this.pooledCacheLanes = 0, this.formState = T, this.transitionTypes = null, this.incompleteTransitions = /* @__PURE__ */ new Map();
  }
  function Zg(t, e, n, l, i, o, s, h, T, z, j, G) {
    return t = new YS(
      t,
      e,
      n,
      s,
      T,
      z,
      j,
      G,
      h
    ), e = 1, o === !0 && (e |= 24), o = Le(3, null, null, e), t.current = o, o.stateNode = t, e = jc(), e.refCount++, t.pooledCache = e, e.refCount++, o.memoizedState = {
      element: l,
      isDehydrated: n,
      cache: e
    }, qc(o), t;
  }
  function Kg(t) {
    return t ? (t = $a, t) : $a;
  }
  function Jg(t, e, n, l, i, o) {
    i = Kg(i), l.context === null ? l.context = i : l.pendingContext = i, l = Dl(e), l.payload = { element: n }, o = o === void 0 ? null : o, o !== null && (l.callback = o), n = zl(t, l, e), n !== null && (Ge(n, t, e), so(n, t, e));
  }
  function Fg(t, e) {
    if (t = t.memoizedState, t !== null && t.dehydrated !== null) {
      var n = t.retryLane;
      t.retryLane = n !== 0 && n < e ? n : e;
    }
  }
  function Tf(t, e) {
    Fg(t, e), (t = t.alternate) && Fg(t, e);
  }
  function $g(t) {
    if (t.tag === 13 || t.tag === 31) {
      var e = ca(t, 67108864);
      e !== null && Ge(e, t, 67108864), Tf(t, 67108864);
    }
  }
  function Ig(t) {
    if (t.tag === 13 || t.tag === 31) {
      var e = en();
      e = nc(e);
      var n = ca(t, e);
      n !== null && Ge(n, t, e), Tf(t, e);
    }
  }
  var Ci = !0;
  function qS(t, e, n, l) {
    var i = lt.T;
    lt.T = null;
    var o = mt.p;
    try {
      mt.p = 2, wf(t, e, n, l);
    } finally {
      mt.p = o, lt.T = i;
    }
  }
  function VS(t, e, n, l) {
    var i = lt.T;
    lt.T = null;
    var o = mt.p;
    try {
      mt.p = 8, wf(t, e, n, l);
    } finally {
      mt.p = o, lt.T = i;
    }
  }
  function wf(t, e, n, l) {
    if (Ci) {
      var i = Cf(l);
      if (i === null)
        af(
          t,
          e,
          l,
          Sr,
          n
        ), Wg(t, l);
      else if (XS(
        i,
        t,
        e,
        n,
        l
      ))
        l.stopPropagation();
      else if (Wg(t, l), e & 4 && -1 < GS.indexOf(t)) {
        for (; i !== null; ) {
          var o = Ya(i);
          if (o !== null)
            switch (o.tag) {
              case 3:
                if (o = o.stateNode, o.current.memoizedState.isDehydrated) {
                  var s = aa(o.pendingLanes);
                  if (s !== 0) {
                    var h = o;
                    for (h.pendingLanes |= 2, h.entangledLanes |= 2; s; ) {
                      var T = 1 << 31 - Ht(s);
                      h.entanglements[1] |= T, s &= ~T;
                    }
                    Vn(o), (jt & 6) === 0 && (ir = Ae() + 500, _o(0));
                  }
                }
                break;
              case 31:
              case 13:
                h = ca(o, 2), h !== null && Ge(h, o, 2), rr(), Tf(o, 2);
            }
          if (o = Cf(l), o === null && af(
            t,
            e,
            l,
            Sr,
            n
          ), o === i) break;
          i = o;
        }
        i !== null && l.stopPropagation();
      } else
        af(
          t,
          e,
          l,
          null,
          n
        );
    }
  }
  function Cf(t) {
    return t = cc(t), Of(t);
  }
  var Sr = null;
  function Of(t) {
    if (Sr = null, t = ia(t), t !== null) {
      var e = m(t);
      if (e === null) t = null;
      else {
        var n = e.tag;
        if (n === 13) {
          if (t = v(e), t !== null) return t;
          t = null;
        } else if (n === 31) {
          if (t = g(e), t !== null) return t;
          t = null;
        } else if (n === 3) {
          if (e.stateNode.current.memoizedState.isDehydrated)
            return e.tag === 3 ? e.stateNode.containerInfo : null;
          t = null;
        } else e !== t && (t = null);
      }
    }
    return Sr = t, null;
  }
  function Pg(t) {
    switch (t) {
      case "beforetoggle":
      case "cancel":
      case "click":
      case "close":
      case "contextmenu":
      case "copy":
      case "cut":
      case "auxclick":
      case "dblclick":
      case "dragend":
      case "dragstart":
      case "drop":
      case "focusin":
      case "focusout":
      case "input":
      case "invalid":
      case "keydown":
      case "keypress":
      case "keyup":
      case "mousedown":
      case "mouseup":
      case "paste":
      case "pause":
      case "play":
      case "pointercancel":
      case "pointerdown":
      case "pointerup":
      case "ratechange":
      case "reset":
      case "seeked":
      case "submit":
      case "toggle":
      case "touchcancel":
      case "touchend":
      case "touchstart":
      case "volumechange":
      case "change":
      case "selectionchange":
      case "textInput":
      case "compositionstart":
      case "compositionend":
      case "compositionupdate":
      case "beforeblur":
      case "afterblur":
      case "beforeinput":
      case "blur":
      case "fullscreenchange":
      case "fullscreenerror":
      case "focus":
      case "hashchange":
      case "popstate":
      case "select":
      case "selectstart":
        return 2;
      case "drag":
      case "dragenter":
      case "dragexit":
      case "dragleave":
      case "dragover":
      case "mousemove":
      case "mouseout":
      case "mouseover":
      case "pointermove":
      case "pointerout":
      case "pointerover":
      case "resize":
      case "scroll":
      case "touchmove":
      case "wheel":
      case "mouseenter":
      case "mouseleave":
      case "pointerenter":
      case "pointerleave":
        return 8;
      case "message":
        switch (Vi()) {
          case En:
            return 2;
          case Gi:
            return 8;
          case Ba:
          case eu:
            return 32;
          case Xi:
            return 268435456;
          default:
            return 32;
        }
      default:
        return 32;
    }
  }
  var _f = !1, kl = null, Ql = null, Zl = null, Ho = /* @__PURE__ */ new Map(), jo = /* @__PURE__ */ new Map(), Kl = [], GS = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset".split(
    " "
  );
  function Wg(t, e) {
    switch (t) {
      case "focusin":
      case "focusout":
        kl = null;
        break;
      case "dragenter":
      case "dragleave":
        Ql = null;
        break;
      case "mouseover":
      case "mouseout":
        Zl = null;
        break;
      case "pointerover":
      case "pointerout":
        Ho.delete(e.pointerId);
        break;
      case "gotpointercapture":
      case "lostpointercapture":
        jo.delete(e.pointerId);
    }
  }
  function Bo(t, e, n, l, i, o) {
    return t === null || t.nativeEvent !== o ? (t = {
      blockedOn: e,
      domEventName: n,
      eventSystemFlags: l,
      nativeEvent: o,
      targetContainers: [i]
    }, e !== null && (e = Ya(e), e !== null && $g(e)), t) : (t.eventSystemFlags |= l, e = t.targetContainers, i !== null && e.indexOf(i) === -1 && e.push(i), t);
  }
  function XS(t, e, n, l, i) {
    switch (e) {
      case "focusin":
        return kl = Bo(
          kl,
          t,
          e,
          n,
          l,
          i
        ), !0;
      case "dragenter":
        return Ql = Bo(
          Ql,
          t,
          e,
          n,
          l,
          i
        ), !0;
      case "mouseover":
        return Zl = Bo(
          Zl,
          t,
          e,
          n,
          l,
          i
        ), !0;
      case "pointerover":
        var o = i.pointerId;
        return Ho.set(
          o,
          Bo(
            Ho.get(o) || null,
            t,
            e,
            n,
            l,
            i
          )
        ), !0;
      case "gotpointercapture":
        return o = i.pointerId, jo.set(
          o,
          Bo(
            jo.get(o) || null,
            t,
            e,
            n,
            l,
            i
          )
        ), !0;
    }
    return !1;
  }
  function t0(t) {
    var e = ia(t.target);
    if (e !== null) {
      var n = m(e);
      if (n !== null) {
        if (e = n.tag, e === 13) {
          if (e = v(n), e !== null) {
            t.blockedOn = e, Zd(t.priority, function() {
              Ig(n);
            });
            return;
          }
        } else if (e === 31) {
          if (e = g(n), e !== null) {
            t.blockedOn = e, Zd(t.priority, function() {
              Ig(n);
            });
            return;
          }
        } else if (e === 3 && n.stateNode.current.memoizedState.isDehydrated) {
          t.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
          return;
        }
      }
    }
    t.blockedOn = null;
  }
  function Er(t) {
    if (t.blockedOn !== null) return !1;
    for (var e = t.targetContainers; 0 < e.length; ) {
      var n = Cf(t.nativeEvent);
      if (n === null) {
        n = t.nativeEvent;
        var l = new n.constructor(
          n.type,
          n
        );
        rc = l, n.target.dispatchEvent(l), rc = null;
      } else
        return e = Ya(n), e !== null && $g(e), t.blockedOn = n, !1;
      e.shift();
    }
    return !0;
  }
  function e0(t, e, n) {
    Er(t) && n.delete(e);
  }
  function kS() {
    _f = !1, kl !== null && Er(kl) && (kl = null), Ql !== null && Er(Ql) && (Ql = null), Zl !== null && Er(Zl) && (Zl = null), Ho.forEach(e0), jo.forEach(e0);
  }
  function xr(t, e) {
    t.blockedOn === e && (t.blockedOn = null, _f || (_f = !0, a.unstable_scheduleCallback(
      a.unstable_NormalPriority,
      kS
    )));
  }
  var Tr = null;
  function n0(t) {
    Tr !== t && (Tr = t, a.unstable_scheduleCallback(
      a.unstable_NormalPriority,
      function() {
        Tr === t && (Tr = null);
        for (var e = 0; e < t.length; e += 3) {
          var n = t[e], l = t[e + 1], i = t[e + 2];
          if (typeof l != "function") {
            if (Of(l || n) === null)
              continue;
            break;
          }
          var o = Ya(n);
          o !== null && (t.splice(e, 3), e -= 3, us(
            o,
            {
              pending: !0,
              data: i,
              method: n.method,
              action: l
            },
            l,
            i
          ));
        }
      }
    ));
  }
  function Oi(t) {
    function e(T) {
      return xr(T, t);
    }
    kl !== null && xr(kl, t), Ql !== null && xr(Ql, t), Zl !== null && xr(Zl, t), Ho.forEach(e), jo.forEach(e);
    for (var n = 0; n < Kl.length; n++) {
      var l = Kl[n];
      l.blockedOn === t && (l.blockedOn = null);
    }
    for (; 0 < Kl.length && (n = Kl[0], n.blockedOn === null); )
      t0(n), n.blockedOn === null && Kl.shift();
    if (n = (t.ownerDocument || t).$$reactFormReplay, n != null)
      for (l = 0; l < n.length; l += 3) {
        var i = n[l], o = n[l + 1], s = i[Be] || null;
        if (typeof o == "function")
          s || n0(n);
        else if (s) {
          var h = null;
          if (o && o.hasAttribute("formAction")) {
            if (i = o, s = o[Be] || null)
              h = s.formAction;
            else if (Of(i) !== null) continue;
          } else h = s.action;
          typeof h == "function" ? n[l + 1] = h : (n.splice(l, 3), l -= 3), n0(n);
        }
      }
  }
  function l0() {
    function t(o) {
      o.canIntercept && o.info === "react-transition" && o.intercept({
        handler: function() {
          return new Promise(function(s) {
            return i = s;
          });
        },
        focusReset: "manual",
        scroll: "manual"
      });
    }
    function e() {
      i !== null && (i(), i = null), l || setTimeout(n, 20);
    }
    function n() {
      if (!l && !navigation.transition) {
        var o = navigation.currentEntry;
        o && o.url != null && navigation.navigate(o.url, {
          state: o.getState(),
          info: "react-transition",
          history: "replace"
        });
      }
    }
    if (typeof navigation == "object") {
      var l = !1, i = null;
      return navigation.addEventListener("navigate", t), navigation.addEventListener("navigatesuccess", e), navigation.addEventListener("navigateerror", e), setTimeout(n, 100), function() {
        l = !0, navigation.removeEventListener("navigate", t), navigation.removeEventListener("navigatesuccess", e), navigation.removeEventListener("navigateerror", e), i !== null && (i(), i = null);
      };
    }
  }
  function Af(t) {
    this._internalRoot = t;
  }
  wr.prototype.render = Af.prototype.render = function(t) {
    var e = this._internalRoot;
    if (e === null) throw Error(c(409));
    var n = e.current, l = en();
    Jg(n, l, t, e, null, null);
  }, wr.prototype.unmount = Af.prototype.unmount = function() {
    var t = this._internalRoot;
    if (t !== null) {
      this._internalRoot = null;
      var e = t.containerInfo;
      Jg(t.current, 2, null, t, null, null), rr(), e[La] = null;
    }
  };
  function wr(t) {
    this._internalRoot = t;
  }
  wr.prototype.unstable_scheduleHydration = function(t) {
    if (t) {
      var e = Qd();
      t = { blockedOn: null, target: t, priority: e };
      for (var n = 0; n < Kl.length && e !== 0 && e < Kl[n].priority; n++) ;
      Kl.splice(n, 0, t), n === 0 && t0(t);
    }
  };
  var a0 = u.version;
  if (a0 !== "19.3.0")
    throw Error(
      c(
        527,
        a0,
        "19.3.0"
      )
    );
  mt.findDOMNode = function(t) {
    var e = t._reactInternals;
    if (e === void 0)
      throw typeof t.render == "function" ? Error(c(188)) : (t = Object.keys(t).join(","), Error(c(268, t)));
    return t = y(e), t = t !== null ? S(t) : null, t = t === null ? null : t.stateNode, t;
  };
  var QS = {
    bundleType: 0,
    version: "19.3.0",
    rendererPackageName: "react-dom",
    currentDispatcherRef: lt,
    reconcilerVersion: "19.3.0"
  };
  if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
    var Cr = __REACT_DEVTOOLS_GLOBAL_HOOK__;
    if (!Cr.isDisabled && Cr.supportsFiber)
      try {
        Wt = Cr.inject(
          QS
        ), Gt = Cr;
      } catch {
      }
  }
  return Yo.createRoot = function(t, e) {
    if (!f(t)) throw Error(c(299));
    var n = !1, l = "", i = Kv, o = Jv, s = Fv;
    return e != null && (e.unstable_strictMode === !0 && (n = !0), e.identifierPrefix !== void 0 && (l = e.identifierPrefix), e.onUncaughtError !== void 0 && (i = e.onUncaughtError), e.onCaughtError !== void 0 && (o = e.onCaughtError), e.onRecoverableError !== void 0 && (s = e.onRecoverableError)), e = Zg(
      t,
      1,
      !1,
      null,
      null,
      n,
      l,
      null,
      i,
      o,
      s,
      l0
    ), t[La] = e.current, lf(t), new Af(e);
  }, Yo.hydrateRoot = function(t, e, n) {
    if (!f(t)) throw Error(c(299));
    var l = !1, i = "", o = Kv, s = Jv, h = Fv, T = null;
    return n != null && (n.unstable_strictMode === !0 && (l = !0), n.identifierPrefix !== void 0 && (i = n.identifierPrefix), n.onUncaughtError !== void 0 && (o = n.onUncaughtError), n.onCaughtError !== void 0 && (s = n.onCaughtError), n.onRecoverableError !== void 0 && (h = n.onRecoverableError), n.formState !== void 0 && (T = n.formState)), e = Zg(
      t,
      1,
      !0,
      e,
      n ?? null,
      l,
      i,
      T,
      o,
      s,
      h,
      l0
    ), e.context = Kg(null), n = e.current, l = en(), l = nc(l), i = Dl(l), i.callback = null, zl(n, i, l), n = l, e.current.lanes = n, Zi(e, n), Vn(e), t[La] = e.current, lf(t), new wr(e);
  }, Yo.version = "19.3.0", Yo;
}
var v0;
function e2() {
  if (v0) return Df.exports;
  v0 = 1;
  function a() {
    if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"))
      try {
        __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(a);
      } catch (u) {
        console.error(u);
      }
  }
  return a(), Df.exports = t2(), Df.exports;
}
var md = e2(), n2 = Object.defineProperty, vd = (a, u) => n2(a, "name", { value: u, configurable: !0 });
function Jf(a, u) {
  if (typeof a == "function")
    return a(u);
  a != null && (a.current = u);
}
vd(Jf, "setRef");
function Ra(...a) {
  return (u) => {
    let r = !1;
    const c = a.map((f) => {
      const m = Jf(f, u);
      return !r && typeof m == "function" && (r = !0), m;
    });
    if (r)
      return () => {
        for (let f = 0; f < c.length; f++) {
          const m = c[f];
          typeof m == "function" ? m() : Jf(a[f], null);
        }
      };
  };
}
vd(Ra, "composeRefs");
function Fn(...a) {
  return b.useCallback(Ra(...a), a);
}
vd(Fn, "useComposedRefs");
var l2 = Object.defineProperty, Rn = (a, u) => l2(a, "name", { value: u, configurable: !0 });
// @__NO_SIDE_EFFECTS__
function kr(a) {
  const u = b.forwardRef((r, c) => {
    let { children: f, ...m } = r, v = null, g = !1;
    const p = [];
    Ff(f) && typeof Or == "function" && (f = Or(f._payload)), b.Children.forEach(f, (x) => {
      var C;
      if (oy(x)) {
        g = !0;
        const R = x;
        let O = "child" in R.props ? R.props.child : R.props.children;
        Ff(O) && typeof Or == "function" && (O = Or(O._payload)), v = i2(R, O), p.push((C = v == null ? void 0 : v.props) == null ? void 0 : C.children);
      } else
        p.push(x);
    }), v ? v = b.cloneElement(v, void 0, p) : (
      // A `Slottable` was found but it didn't resolve to a single element (e.g.
      // it wrapped multiple elements, text, or a render-prop `child` that
      // wasn't an element). Don't fall back to treating the `Slottable` wrapper
      // itself as the slot target — throw a descriptive error below instead.
      !g && b.Children.count(f) === 1 && b.isValidElement(f) && (v = f)
    );
    const y = v ? iy(v) : void 0, S = Fn(c, y);
    if (!v) {
      if (f || f === 0)
        throw new Error(
          g ? r2(a) : u2(a)
        );
      return f;
    }
    const d = ay(m, v.props ?? {});
    return v.type !== b.Fragment && (d.ref = c ? S : y), b.cloneElement(v, d);
  });
  return u.displayName = `${a}.Slot`, u;
}
Rn(kr, "createSlot");
var a2 = /* @__PURE__ */ kr("Slot"), ny = Symbol.for("radix.slottable");
// @__NO_SIDE_EFFECTS__
function ly(a) {
  const u = /* @__PURE__ */ Rn((r) => "child" in r ? r.children(r.child) : r.children, "Slottable");
  return u.displayName = `${a}.Slottable`, u.__radixId = ny, u;
}
Rn(ly, "createSlottable");
var i2 = /* @__PURE__ */ Rn((a, u) => {
  if ("child" in a.props) {
    const r = a.props.child;
    return b.isValidElement(r) ? b.cloneElement(r, void 0, a.props.children(r.props.children)) : null;
  }
  return b.isValidElement(u) ? u : null;
}, "getSlottableElementFromSlottable");
function ay(a, u) {
  const r = { ...u };
  for (const c in u) {
    const f = a[c], m = u[c];
    /^on[A-Z]/.test(c) ? f && m ? r[c] = (...g) => {
      const p = m(...g);
      return f(...g), p;
    } : f && (r[c] = f) : c === "style" ? r[c] = { ...f, ...m } : c === "className" && (r[c] = [f, m].filter(Boolean).join(" "));
  }
  return { ...a, ...r };
}
Rn(ay, "mergeProps");
function iy(a) {
  var c, f;
  let u = (c = Object.getOwnPropertyDescriptor(a.props, "ref")) == null ? void 0 : c.get, r = u && "isReactWarning" in u && u.isReactWarning;
  return r ? a.ref : (u = (f = Object.getOwnPropertyDescriptor(a, "ref")) == null ? void 0 : f.get, r = u && "isReactWarning" in u && u.isReactWarning, r ? a.props.ref : a.props.ref || a.ref);
}
Rn(iy, "getElementRef");
function oy(a) {
  return b.isValidElement(a) && typeof a.type == "function" && "__radixId" in a.type && a.type.__radixId === ny;
}
Rn(oy, "isSlottable");
var o2 = Symbol.for("react.lazy");
function Ff(a) {
  return a != null && typeof a == "object" && "$$typeof" in a && a.$$typeof === o2 && "_payload" in a && uy(a._payload);
}
Rn(Ff, "isLazyComponent");
function uy(a) {
  return typeof a == "object" && a !== null && "then" in a;
}
Rn(uy, "isPromiseLike");
var u2 = /* @__PURE__ */ Rn((a) => `${a} failed to slot onto its children. Expected a single React element child or \`Slottable\`.`, "createSlotError"), r2 = /* @__PURE__ */ Rn((a) => `${a} failed to slot onto its \`Slottable\`. Expected \`Slottable\` to receive a single React element child.`, "createSlottableError"), Or = Ko[" use ".trim().toString()];
function ry(a) {
  var u, r, c = "";
  if (typeof a == "string" || typeof a == "number") c += a;
  else if (typeof a == "object") if (Array.isArray(a)) {
    var f = a.length;
    for (u = 0; u < f; u++) a[u] && (r = ry(a[u])) && (c && (c += " "), c += r);
  } else for (r in a) a[r] && (c && (c += " "), c += r);
  return c;
}
function cy() {
  for (var a, u, r = 0, c = "", f = arguments.length; r < f; r++) (a = arguments[r]) && (u = ry(a)) && (c && (c += " "), c += u);
  return c;
}
const h0 = (a) => typeof a == "boolean" ? `${a}` : a === 0 ? "0" : a, g0 = cy, c2 = (a, u) => (r) => {
  var c;
  if ((u == null ? void 0 : u.variants) == null) return g0(a, r == null ? void 0 : r.class, r == null ? void 0 : r.className);
  const { variants: f, defaultVariants: m } = u, v = Object.keys(f).map((y) => {
    const S = r == null ? void 0 : r[y], d = m == null ? void 0 : m[y];
    if (S === null) return null;
    const x = h0(S) || h0(d);
    return f[y][x];
  }), g = r && Object.entries(r).reduce((y, S) => {
    let [d, x] = S;
    return x === void 0 || (y[d] = x), y;
  }, {}), p = u == null || (c = u.compoundVariants) === null || c === void 0 ? void 0 : c.reduce((y, S) => {
    let { class: d, className: x, ...C } = S;
    return Object.entries(C).every((R) => {
      let [O, N] = R;
      return Array.isArray(N) ? N.includes({
        ...m,
        ...g
      }[O]) : {
        ...m,
        ...g
      }[O] === N;
    }) ? [
      ...y,
      d,
      x
    ] : y;
  }, []);
  return g0(a, v, p, r == null ? void 0 : r.class, r == null ? void 0 : r.className);
}, s2 = (a, u) => {
  const r = new Array(a.length + u.length);
  for (let c = 0; c < a.length; c++)
    r[c] = a[c];
  for (let c = 0; c < u.length; c++)
    r[a.length + c] = u[c];
  return r;
}, f2 = (a, u) => ({
  classGroupId: a,
  validator: u
}), sy = (a = /* @__PURE__ */ new Map(), u = null, r) => ({
  nextPart: a,
  validators: u,
  classGroupId: r
}), Yr = "-", y0 = [], d2 = "arbitrary..", m2 = (a) => {
  const u = h2(a), {
    conflictingClassGroups: r,
    conflictingClassGroupModifiers: c
  } = a;
  return {
    getClassGroupId: (v) => {
      if (v.startsWith("[") && v.endsWith("]"))
        return v2(v);
      const g = v.split(Yr), p = g[0] === "" && g.length > 1 ? 1 : 0;
      return fy(g, p, u);
    },
    getConflictingClassGroupIds: (v, g) => {
      if (g) {
        const p = c[v], y = r[v];
        return p ? y ? s2(y, p) : p : y || y0;
      }
      return r[v] || y0;
    }
  };
}, fy = (a, u, r) => {
  if (a.length - u === 0)
    return r.classGroupId;
  const f = a[u], m = r.nextPart.get(f);
  if (m) {
    const y = fy(a, u + 1, m);
    if (y) return y;
  }
  const v = r.validators;
  if (v === null)
    return;
  const g = u === 0 ? a.join(Yr) : a.slice(u).join(Yr), p = v.length;
  for (let y = 0; y < p; y++) {
    const S = v[y];
    if (S.validator(g))
      return S.classGroupId;
  }
}, v2 = (a) => a.slice(1, -1).indexOf(":") === -1 ? void 0 : (() => {
  const u = a.slice(1, -1), r = u.indexOf(":"), c = u.slice(0, r);
  return c ? d2 + c : void 0;
})(), h2 = (a) => {
  const {
    theme: u,
    classGroups: r
  } = a;
  return g2(r, u);
}, g2 = (a, u) => {
  const r = sy();
  for (const c in a) {
    const f = a[c];
    hd(f, r, c, u);
  }
  return r;
}, hd = (a, u, r, c) => {
  const f = a.length;
  for (let m = 0; m < f; m++) {
    const v = a[m];
    y2(v, u, r, c);
  }
}, y2 = (a, u, r, c) => {
  if (typeof a == "string") {
    p2(a, u, r);
    return;
  }
  if (typeof a == "function") {
    b2(a, u, r, c);
    return;
  }
  S2(a, u, r, c);
}, p2 = (a, u, r) => {
  const c = a === "" ? u : dy(u, a);
  c.classGroupId = r;
}, b2 = (a, u, r, c) => {
  if (E2(a)) {
    hd(a(c), u, r, c);
    return;
  }
  u.validators === null && (u.validators = []), u.validators.push(f2(r, a));
}, S2 = (a, u, r, c) => {
  const f = Object.entries(a), m = f.length;
  for (let v = 0; v < m; v++) {
    const [g, p] = f[v];
    hd(p, dy(u, g), r, c);
  }
}, dy = (a, u) => {
  let r = a;
  const c = u.split(Yr), f = c.length;
  for (let m = 0; m < f; m++) {
    const v = c[m];
    let g = r.nextPart.get(v);
    g || (g = sy(), r.nextPart.set(v, g)), r = g;
  }
  return r;
}, E2 = (a) => "isThemeGetter" in a && a.isThemeGetter === !0, x2 = (a) => {
  if (a < 1)
    return {
      get: () => {
      },
      set: () => {
      }
    };
  let u = 0, r = /* @__PURE__ */ Object.create(null), c = /* @__PURE__ */ Object.create(null);
  const f = (m, v) => {
    r[m] = v, u++, u > a && (u = 0, c = r, r = /* @__PURE__ */ Object.create(null));
  };
  return {
    get(m) {
      let v = r[m];
      if (v !== void 0)
        return v;
      if ((v = c[m]) !== void 0)
        return f(m, v), v;
    },
    set(m, v) {
      m in r ? r[m] = v : f(m, v);
    }
  };
}, $f = "!", p0 = ":", T2 = [], b0 = (a, u, r, c, f) => ({
  modifiers: a,
  hasImportantModifier: u,
  baseClassName: r,
  maybePostfixModifierPosition: c,
  isExternal: f
}), w2 = (a) => {
  const {
    prefix: u,
    experimentalParseClassName: r
  } = a;
  let c = (f) => {
    const m = [];
    let v = 0, g = 0, p = 0, y;
    const S = f.length;
    for (let O = 0; O < S; O++) {
      const N = f[O];
      if (v === 0 && g === 0) {
        if (N === p0) {
          m.push(f.slice(p, O)), p = O + 1;
          continue;
        }
        if (N === "/") {
          y = O;
          continue;
        }
      }
      N === "[" ? v++ : N === "]" ? v-- : N === "(" ? g++ : N === ")" && g--;
    }
    const d = m.length === 0 ? f : f.slice(p);
    let x = d, C = !1;
    d.endsWith($f) ? (x = d.slice(0, -1), C = !0) : (
      /**
       * In Tailwind CSS v3 the important modifier was at the start of the base class name. This is still supported for legacy reasons.
       * @see https://github.com/dcastil/tailwind-merge/issues/513#issuecomment-2614029864
       */
      d.startsWith($f) && (x = d.slice(1), C = !0)
    );
    const R = y && y > p ? y - p : void 0;
    return b0(m, C, x, R);
  };
  if (u) {
    const f = u + p0, m = c;
    c = (v) => v.startsWith(f) ? m(v.slice(f.length)) : b0(T2, !1, v, void 0, !0);
  }
  if (r) {
    const f = c;
    c = (m) => r({
      className: m,
      parseClassName: f
    });
  }
  return c;
}, C2 = (a) => {
  const u = /* @__PURE__ */ new Map();
  return a.orderSensitiveModifiers.forEach((r, c) => {
    u.set(r, 1e6 + c);
  }), (r) => {
    const c = [];
    let f = [];
    for (let m = 0; m < r.length; m++) {
      const v = r[m], g = v[0] === "[", p = u.has(v);
      g || p ? (f.length > 0 && (f.sort(), c.push(...f), f = []), c.push(v)) : f.push(v);
    }
    return f.length > 0 && (f.sort(), c.push(...f)), c;
  };
}, O2 = (a) => ({
  cache: x2(a.cacheSize),
  parseClassName: w2(a),
  sortModifiers: C2(a),
  postfixLookupClassGroupIds: _2(a),
  ...m2(a)
}), _2 = (a) => {
  const u = /* @__PURE__ */ Object.create(null), r = a.postfixLookupClassGroups;
  if (r)
    for (let c = 0; c < r.length; c++)
      u[r[c]] = !0;
  return u;
}, A2 = /\s+/, R2 = (a, u) => {
  const {
    parseClassName: r,
    getClassGroupId: c,
    getConflictingClassGroupIds: f,
    sortModifiers: m,
    postfixLookupClassGroupIds: v
  } = u, g = [], p = a.trim().split(A2);
  let y = "";
  for (let S = p.length - 1; S >= 0; S -= 1) {
    const d = p[S], {
      isExternal: x,
      modifiers: C,
      hasImportantModifier: R,
      baseClassName: O,
      maybePostfixModifierPosition: N
    } = r(d);
    if (x) {
      y = d + (y.length > 0 ? " " + y : y);
      continue;
    }
    let H = !!N, L;
    if (H) {
      const X = O.substring(0, N);
      L = c(X);
      const Y = L && v[L] ? c(O) : void 0;
      Y && Y !== L && (L = Y, H = !1);
    } else
      L = c(O);
    if (!L) {
      if (!H) {
        y = d + (y.length > 0 ? " " + y : y);
        continue;
      }
      if (L = c(O), !L) {
        y = d + (y.length > 0 ? " " + y : y);
        continue;
      }
      H = !1;
    }
    const J = C.length === 0 ? "" : C.length === 1 ? C[0] : m(C).join(":"), K = R ? J + $f : J, I = K + L;
    if (g.indexOf(I) > -1)
      continue;
    g.push(I);
    const Z = f(L, H);
    for (let X = 0; X < Z.length; ++X) {
      const Y = Z[X];
      g.push(K + Y);
    }
    y = d + (y.length > 0 ? " " + y : y);
  }
  return y;
}, N2 = (...a) => {
  let u = 0, r, c, f = "";
  for (; u < a.length; )
    (r = a[u++]) && (c = my(r)) && (f && (f += " "), f += c);
  return f;
}, my = (a) => {
  if (typeof a == "string")
    return a;
  let u, r = "";
  for (let c = 0; c < a.length; c++)
    a[c] && (u = my(a[c])) && (r && (r += " "), r += u);
  return r;
}, D2 = (a, ...u) => {
  let r, c, f, m;
  const v = (p) => {
    const y = u.reduce((S, d) => d(S), a());
    return r = O2(y), c = r.cache.get, f = r.cache.set, m = g, g(p);
  }, g = (p) => {
    const y = c(p);
    if (y)
      return y;
    const S = R2(p, r);
    return f(p, S), S;
  };
  return m = v, (...p) => m(N2(...p));
}, z2 = [], ce = (a) => {
  const u = (r) => r[a] || z2;
  return u.isThemeGetter = !0, u.themeKey = a, u;
}, vy = /^\[(?:(\w[\w-]*):)?(.+)\]$/i, hy = /^\((?:(\w[\w-]*):)?(.+)\)$/i, M2 = /^\d+(?:\.\d+)?\/\d+(?:\.\d+)?$/, U2 = /^(\d+(\.\d+)?)?(xs|sm|md|lg|xl)$/, H2 = /\d+(%|px|r?em|[sdl]?v([hwib]|min|max)|pt|pc|in|cm|mm|cap|ch|ex|r?lh|cq(w|h|i|b|min|max))|\b(calc|min|max|clamp)\(.+\)|^0$/, j2 = /^(rgba?|hsla?|hwb|(ok)?(lab|lch)|color-mix|color|light-dark)\(.+\)$/, B2 = /^(inset_)?-?((\d+)?\.?(\d+)[a-z]+|0)_-?((\d+)?\.?(\d+)[a-z]+|0)/, L2 = /^(url|image|image-set|cross-fade|element|(repeating-)?(linear|radial|conic)-gradient)\(.+\)$/, Fl = (a) => M2.test(a), _t = (a) => !!a && !Number.isNaN(Number(a)), Gn = (a) => !!a && Number.isInteger(Number(a)), Hf = (a) => a.endsWith("%") && _t(a.slice(0, -1)), vl = (a) => U2.test(a), gy = () => !0, Y2 = (a) => (
  // `colorFunctionRegex` check is necessary because color functions can have percentages in them which which would be incorrectly classified as lengths.
  // For example, `hsl(0 0% 0%)` would be classified as a length without this check.
  // I could also use lookbehind assertion in `lengthUnitRegex` but that isn't supported widely enough.
  H2.test(a) && !j2.test(a)
), gd = () => !1, q2 = (a) => B2.test(a), V2 = (a) => L2.test(a), G2 = (a) => !ot(a) && !ut(a), X2 = (a) => a.startsWith("@container") && (a[10] === "/" && a[11] !== void 0 || a[11] === "s" && a[16] !== void 0 && a.startsWith("-size/", 10) || a[11] === "n" && a[18] !== void 0 && a.startsWith("-normal/", 10)), k2 = (a) => ta(a, by, gd), ot = (a) => vy.test(a), _a = (a) => ta(a, Sy, Y2), S0 = (a) => ta(a, P2, _t), Q2 = (a) => ta(a, xy, gy), Z2 = (a) => ta(a, Ey, gd), E0 = (a) => ta(a, yy, gd), K2 = (a) => ta(a, py, V2), _r = (a) => ta(a, Ty, q2), ut = (a) => hy.test(a), qo = (a) => Ua(a, Sy), J2 = (a) => Ua(a, Ey), x0 = (a) => Ua(a, yy), F2 = (a) => Ua(a, by), $2 = (a) => Ua(a, py), Ar = (a) => Ua(a, Ty, !0), I2 = (a) => Ua(a, xy, !0), ta = (a, u, r) => {
  const c = vy.exec(a);
  return c ? c[1] ? u(c[1]) : r(c[2]) : !1;
}, Ua = (a, u, r = !1) => {
  const c = hy.exec(a);
  return c ? c[1] ? u(c[1]) : r : !1;
}, yy = (a) => a === "position" || a === "percentage", py = (a) => a === "image" || a === "url", by = (a) => a === "length" || a === "size" || a === "bg-size", Sy = (a) => a === "length", P2 = (a) => a === "number", Ey = (a) => a === "family-name", xy = (a) => a === "number" || a === "weight", Ty = (a) => a === "shadow", W2 = () => {
  const a = ce("color"), u = ce("font"), r = ce("text"), c = ce("font-weight"), f = ce("tracking"), m = ce("leading"), v = ce("breakpoint"), g = ce("container"), p = ce("spacing"), y = ce("radius"), S = ce("shadow"), d = ce("inset-shadow"), x = ce("text-shadow"), C = ce("drop-shadow"), R = ce("blur"), O = ce("perspective"), N = ce("aspect"), H = ce("ease"), L = ce("animate"), J = () => ["auto", "avoid", "all", "avoid-page", "page", "left", "right", "column"], K = () => [
    "center",
    "top",
    "bottom",
    "left",
    "right",
    "top-left",
    // Deprecated since Tailwind CSS v4.1.0, see https://github.com/tailwindlabs/tailwindcss/pull/17378
    "left-top",
    "top-right",
    // Deprecated since Tailwind CSS v4.1.0, see https://github.com/tailwindlabs/tailwindcss/pull/17378
    "right-top",
    "bottom-right",
    // Deprecated since Tailwind CSS v4.1.0, see https://github.com/tailwindlabs/tailwindcss/pull/17378
    "right-bottom",
    "bottom-left",
    // Deprecated since Tailwind CSS v4.1.0, see https://github.com/tailwindlabs/tailwindcss/pull/17378
    "left-bottom"
  ], I = () => [...K(), ut, ot], Z = () => ["auto", "hidden", "clip", "visible", "scroll"], X = () => ["auto", "contain", "none"], Y = () => [ut, ot, p], dt = () => [Fl, "full", "auto", ...Y()], ht = () => [Gn, "none", "subgrid", ut, ot], xt = () => ["auto", {
    span: ["full", Gn, ut, ot]
  }, Gn, ut, ot], st = () => [Gn, "auto", ut, ot], Tt = () => ["auto", "min", "max", "fr", ut, ot], gt = () => ["start", "end", "center", "between", "around", "evenly", "stretch", "baseline", "center-safe", "end-safe"], yt = () => ["start", "end", "center", "stretch", "center-safe", "end-safe"], B = () => ["auto", ...Y()], tt = () => [Fl, "auto", "full", "dvw", "dvh", "lvw", "lvh", "svw", "svh", "min", "max", "fit", ...Y()], P = () => [g, Fl, "screen", "full", "dvw", "lvw", "svw", "min", "max", "fit", ...Y()], at = () => [Fl, "screen", "full", "lh", "dvh", "lvh", "svh", "min", "max", "fit", ...Y()], F = () => [a, ut, ot], Bt = () => [...K(), x0, E0, {
    position: [ut, ot]
  }], Q = () => ["no-repeat", {
    repeat: ["", "x", "y", "space", "round"]
  }], rt = () => ["auto", "cover", "contain", F2, k2, {
    size: [ut, ot]
  }], E = () => [Hf, qo, _a], _ = () => [
    // Deprecated since Tailwind CSS v4.0.0
    "",
    "none",
    "full",
    y,
    ut,
    ot
  ], V = () => ["", _t, qo, _a], $ = () => ["solid", "dashed", "dotted", "double"], ft = () => ["normal", "multiply", "screen", "overlay", "darken", "lighten", "color-dodge", "color-burn", "hard-light", "soft-light", "difference", "exclusion", "hue", "saturation", "color", "luminosity"], W = () => [_t, Hf, x0, E0], bt = () => [
    // Deprecated since Tailwind CSS v4.0.0
    "",
    "none",
    R,
    ut,
    ot
  ], lt = () => ["none", _t, ut, ot], mt = () => ["none", _t, ut, ot], It = () => [_t, ut, ot], _e = () => [Fl, "full", ...Y()];
  return {
    cacheSize: 500,
    theme: {
      animate: ["spin", "ping", "pulse", "bounce"],
      aspect: ["video"],
      blur: [vl],
      breakpoint: [vl],
      color: [gy],
      container: [vl],
      "drop-shadow": [vl],
      ease: ["in", "out", "in-out"],
      font: [G2],
      "font-weight": ["thin", "extralight", "light", "normal", "medium", "semibold", "bold", "extrabold", "black"],
      "inset-shadow": [vl],
      leading: ["none", "tight", "snug", "normal", "relaxed", "loose"],
      perspective: ["dramatic", "near", "normal", "midrange", "distant", "none"],
      radius: [vl],
      shadow: [vl],
      spacing: ["px", _t],
      text: [vl],
      "text-shadow": [vl],
      tracking: ["tighter", "tight", "normal", "wide", "wider", "widest"]
    },
    classGroups: {
      // --------------
      // --- Layout ---
      // --------------
      /**
       * Aspect Ratio
       * @see https://tailwindcss.com/docs/aspect-ratio
       */
      aspect: [{
        aspect: ["auto", "square", Fl, ot, ut, N]
      }],
      /**
       * Container
       * @see https://tailwindcss.com/docs/container
       * @deprecated since Tailwind CSS v4.0.0
       */
      container: ["container"],
      /**
       * Container Type
       * @see https://tailwindcss.com/docs/responsive-design#container-queries
       */
      "container-type": [{
        "@container": ["", "normal", "size", ut, ot]
      }],
      /**
       * Container Name
       * @see https://tailwindcss.com/docs/responsive-design#named-containers
       */
      "container-named": [X2],
      /**
       * Columns
       * @see https://tailwindcss.com/docs/columns
       */
      columns: [{
        columns: [_t, "auto", ot, ut, g]
      }],
      /**
       * Break After
       * @see https://tailwindcss.com/docs/break-after
       */
      "break-after": [{
        "break-after": J()
      }],
      /**
       * Break Before
       * @see https://tailwindcss.com/docs/break-before
       */
      "break-before": [{
        "break-before": J()
      }],
      /**
       * Break Inside
       * @see https://tailwindcss.com/docs/break-inside
       */
      "break-inside": [{
        "break-inside": ["auto", "avoid", "avoid-page", "avoid-column"]
      }],
      /**
       * Box Decoration Break
       * @see https://tailwindcss.com/docs/box-decoration-break
       */
      "box-decoration": [{
        "box-decoration": ["slice", "clone"]
      }],
      /**
       * Box Sizing
       * @see https://tailwindcss.com/docs/box-sizing
       */
      box: [{
        box: ["border", "content"]
      }],
      /**
       * Display
       * @see https://tailwindcss.com/docs/display
       */
      display: ["block", "inline-block", "inline", "flex", "inline-flex", "table", "inline-table", "table-caption", "table-cell", "table-column", "table-column-group", "table-footer-group", "table-header-group", "table-row-group", "table-row", "flow-root", "grid", "inline-grid", "contents", "list-item", "hidden"],
      /**
       * Screen Reader Only
       * @see https://tailwindcss.com/docs/display#screen-reader-only
       */
      sr: ["sr-only", "not-sr-only"],
      /**
       * Floats
       * @see https://tailwindcss.com/docs/float
       */
      float: [{
        float: ["right", "left", "none", "start", "end"]
      }],
      /**
       * Clear
       * @see https://tailwindcss.com/docs/clear
       */
      clear: [{
        clear: ["left", "right", "both", "none", "start", "end"]
      }],
      /**
       * Isolation
       * @see https://tailwindcss.com/docs/isolation
       */
      isolation: ["isolate", "isolation-auto"],
      /**
       * Object Fit
       * @see https://tailwindcss.com/docs/object-fit
       */
      "object-fit": [{
        object: ["contain", "cover", "fill", "none", "scale-down"]
      }],
      /**
       * Object Position
       * @see https://tailwindcss.com/docs/object-position
       */
      "object-position": [{
        object: I()
      }],
      /**
       * Overflow
       * @see https://tailwindcss.com/docs/overflow
       */
      overflow: [{
        overflow: Z()
      }],
      /**
       * Overflow X
       * @see https://tailwindcss.com/docs/overflow
       */
      "overflow-x": [{
        "overflow-x": Z()
      }],
      /**
       * Overflow Y
       * @see https://tailwindcss.com/docs/overflow
       */
      "overflow-y": [{
        "overflow-y": Z()
      }],
      /**
       * Overscroll Behavior
       * @see https://tailwindcss.com/docs/overscroll-behavior
       */
      overscroll: [{
        overscroll: X()
      }],
      /**
       * Overscroll Behavior X
       * @see https://tailwindcss.com/docs/overscroll-behavior
       */
      "overscroll-x": [{
        "overscroll-x": X()
      }],
      /**
       * Overscroll Behavior Y
       * @see https://tailwindcss.com/docs/overscroll-behavior
       */
      "overscroll-y": [{
        "overscroll-y": X()
      }],
      /**
       * Position
       * @see https://tailwindcss.com/docs/position
       */
      position: ["static", "fixed", "absolute", "relative", "sticky"],
      /**
       * Inset
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      inset: [{
        inset: dt()
      }],
      /**
       * Inset Inline
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      "inset-x": [{
        "inset-x": dt()
      }],
      /**
       * Inset Block
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      "inset-y": [{
        "inset-y": dt()
      }],
      /**
       * Inset Inline Start
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       * @todo class group will be renamed to `inset-s` in next major release
       */
      start: [{
        "inset-s": dt(),
        /**
         * @deprecated since Tailwind CSS v4.2.0 in favor of `inset-s-*` utilities.
         * @see https://github.com/tailwindlabs/tailwindcss/pull/19613
         */
        start: dt()
      }],
      /**
       * Inset Inline End
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       * @todo class group will be renamed to `inset-e` in next major release
       */
      end: [{
        "inset-e": dt(),
        /**
         * @deprecated since Tailwind CSS v4.2.0 in favor of `inset-e-*` utilities.
         * @see https://github.com/tailwindlabs/tailwindcss/pull/19613
         */
        end: dt()
      }],
      /**
       * Inset Block Start
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      "inset-bs": [{
        "inset-bs": dt()
      }],
      /**
       * Inset Block End
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      "inset-be": [{
        "inset-be": dt()
      }],
      /**
       * Top
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      top: [{
        top: dt()
      }],
      /**
       * Right
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      right: [{
        right: dt()
      }],
      /**
       * Bottom
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      bottom: [{
        bottom: dt()
      }],
      /**
       * Left
       * @see https://tailwindcss.com/docs/top-right-bottom-left
       */
      left: [{
        left: dt()
      }],
      /**
       * Visibility
       * @see https://tailwindcss.com/docs/visibility
       */
      visibility: ["visible", "invisible", "collapse"],
      /**
       * Z-Index
       * @see https://tailwindcss.com/docs/z-index
       */
      z: [{
        z: [Gn, "auto", ut, ot]
      }],
      // ------------------------
      // --- Flexbox and Grid ---
      // ------------------------
      /**
       * Flex Basis
       * @see https://tailwindcss.com/docs/flex-basis
       */
      basis: [{
        basis: [Fl, "full", "auto", g, ...Y()]
      }],
      /**
       * Flex Direction
       * @see https://tailwindcss.com/docs/flex-direction
       */
      "flex-direction": [{
        flex: ["row", "row-reverse", "col", "col-reverse"]
      }],
      /**
       * Flex Wrap
       * @see https://tailwindcss.com/docs/flex-wrap
       */
      "flex-wrap": [{
        flex: ["nowrap", "wrap", "wrap-reverse"]
      }],
      /**
       * Flex
       * @see https://tailwindcss.com/docs/flex
       */
      flex: [{
        flex: [_t, Fl, "auto", "initial", "none", ot]
      }],
      /**
       * Flex Grow
       * @see https://tailwindcss.com/docs/flex-grow
       */
      grow: [{
        grow: ["", _t, ut, ot]
      }],
      /**
       * Flex Shrink
       * @see https://tailwindcss.com/docs/flex-shrink
       */
      shrink: [{
        shrink: ["", _t, ut, ot]
      }],
      /**
       * Order
       * @see https://tailwindcss.com/docs/order
       */
      order: [{
        order: [Gn, "first", "last", "none", ut, ot]
      }],
      /**
       * Grid Template Columns
       * @see https://tailwindcss.com/docs/grid-template-columns
       */
      "grid-cols": [{
        "grid-cols": ht()
      }],
      /**
       * Grid Column Start / End
       * @see https://tailwindcss.com/docs/grid-column
       */
      "col-start-end": [{
        col: xt()
      }],
      /**
       * Grid Column Start
       * @see https://tailwindcss.com/docs/grid-column
       */
      "col-start": [{
        "col-start": st()
      }],
      /**
       * Grid Column End
       * @see https://tailwindcss.com/docs/grid-column
       */
      "col-end": [{
        "col-end": st()
      }],
      /**
       * Grid Template Rows
       * @see https://tailwindcss.com/docs/grid-template-rows
       */
      "grid-rows": [{
        "grid-rows": ht()
      }],
      /**
       * Grid Row Start / End
       * @see https://tailwindcss.com/docs/grid-row
       */
      "row-start-end": [{
        row: xt()
      }],
      /**
       * Grid Row Start
       * @see https://tailwindcss.com/docs/grid-row
       */
      "row-start": [{
        "row-start": st()
      }],
      /**
       * Grid Row End
       * @see https://tailwindcss.com/docs/grid-row
       */
      "row-end": [{
        "row-end": st()
      }],
      /**
       * Grid Auto Flow
       * @see https://tailwindcss.com/docs/grid-auto-flow
       */
      "grid-flow": [{
        "grid-flow": ["row", "col", "dense", "row-dense", "col-dense"]
      }],
      /**
       * Grid Auto Columns
       * @see https://tailwindcss.com/docs/grid-auto-columns
       */
      "auto-cols": [{
        "auto-cols": Tt()
      }],
      /**
       * Grid Auto Rows
       * @see https://tailwindcss.com/docs/grid-auto-rows
       */
      "auto-rows": [{
        "auto-rows": Tt()
      }],
      /**
       * Gap
       * @see https://tailwindcss.com/docs/gap
       */
      gap: [{
        gap: Y()
      }],
      /**
       * Gap X
       * @see https://tailwindcss.com/docs/gap
       */
      "gap-x": [{
        "gap-x": Y()
      }],
      /**
       * Gap Y
       * @see https://tailwindcss.com/docs/gap
       */
      "gap-y": [{
        "gap-y": Y()
      }],
      /**
       * Justify Content
       * @see https://tailwindcss.com/docs/justify-content
       */
      "justify-content": [{
        justify: [...gt(), "normal"]
      }],
      /**
       * Justify Items
       * @see https://tailwindcss.com/docs/justify-items
       */
      "justify-items": [{
        "justify-items": [...yt(), "normal"]
      }],
      /**
       * Justify Self
       * @see https://tailwindcss.com/docs/justify-self
       */
      "justify-self": [{
        "justify-self": ["auto", ...yt()]
      }],
      /**
       * Align Content
       * @see https://tailwindcss.com/docs/align-content
       */
      "align-content": [{
        content: ["normal", ...gt()]
      }],
      /**
       * Align Items
       * @see https://tailwindcss.com/docs/align-items
       */
      "align-items": [{
        items: [...yt(), {
          baseline: ["", "last"]
        }]
      }],
      /**
       * Align Self
       * @see https://tailwindcss.com/docs/align-self
       */
      "align-self": [{
        self: ["auto", ...yt(), {
          baseline: ["", "last"]
        }]
      }],
      /**
       * Place Content
       * @see https://tailwindcss.com/docs/place-content
       */
      "place-content": [{
        "place-content": gt()
      }],
      /**
       * Place Items
       * @see https://tailwindcss.com/docs/place-items
       */
      "place-items": [{
        "place-items": [...yt(), "baseline"]
      }],
      /**
       * Place Self
       * @see https://tailwindcss.com/docs/place-self
       */
      "place-self": [{
        "place-self": ["auto", ...yt()]
      }],
      // Spacing
      /**
       * Padding
       * @see https://tailwindcss.com/docs/padding
       */
      p: [{
        p: Y()
      }],
      /**
       * Padding Inline
       * @see https://tailwindcss.com/docs/padding
       */
      px: [{
        px: Y()
      }],
      /**
       * Padding Block
       * @see https://tailwindcss.com/docs/padding
       */
      py: [{
        py: Y()
      }],
      /**
       * Padding Inline Start
       * @see https://tailwindcss.com/docs/padding
       */
      ps: [{
        ps: Y()
      }],
      /**
       * Padding Inline End
       * @see https://tailwindcss.com/docs/padding
       */
      pe: [{
        pe: Y()
      }],
      /**
       * Padding Block Start
       * @see https://tailwindcss.com/docs/padding
       */
      pbs: [{
        pbs: Y()
      }],
      /**
       * Padding Block End
       * @see https://tailwindcss.com/docs/padding
       */
      pbe: [{
        pbe: Y()
      }],
      /**
       * Padding Top
       * @see https://tailwindcss.com/docs/padding
       */
      pt: [{
        pt: Y()
      }],
      /**
       * Padding Right
       * @see https://tailwindcss.com/docs/padding
       */
      pr: [{
        pr: Y()
      }],
      /**
       * Padding Bottom
       * @see https://tailwindcss.com/docs/padding
       */
      pb: [{
        pb: Y()
      }],
      /**
       * Padding Left
       * @see https://tailwindcss.com/docs/padding
       */
      pl: [{
        pl: Y()
      }],
      /**
       * Margin
       * @see https://tailwindcss.com/docs/margin
       */
      m: [{
        m: B()
      }],
      /**
       * Margin Inline
       * @see https://tailwindcss.com/docs/margin
       */
      mx: [{
        mx: B()
      }],
      /**
       * Margin Block
       * @see https://tailwindcss.com/docs/margin
       */
      my: [{
        my: B()
      }],
      /**
       * Margin Inline Start
       * @see https://tailwindcss.com/docs/margin
       */
      ms: [{
        ms: B()
      }],
      /**
       * Margin Inline End
       * @see https://tailwindcss.com/docs/margin
       */
      me: [{
        me: B()
      }],
      /**
       * Margin Block Start
       * @see https://tailwindcss.com/docs/margin
       */
      mbs: [{
        mbs: B()
      }],
      /**
       * Margin Block End
       * @see https://tailwindcss.com/docs/margin
       */
      mbe: [{
        mbe: B()
      }],
      /**
       * Margin Top
       * @see https://tailwindcss.com/docs/margin
       */
      mt: [{
        mt: B()
      }],
      /**
       * Margin Right
       * @see https://tailwindcss.com/docs/margin
       */
      mr: [{
        mr: B()
      }],
      /**
       * Margin Bottom
       * @see https://tailwindcss.com/docs/margin
       */
      mb: [{
        mb: B()
      }],
      /**
       * Margin Left
       * @see https://tailwindcss.com/docs/margin
       */
      ml: [{
        ml: B()
      }],
      /**
       * Space Between X
       * @see https://tailwindcss.com/docs/margin#adding-space-between-children
       */
      "space-x": [{
        "space-x": Y()
      }],
      /**
       * Space Between X Reverse
       * @see https://tailwindcss.com/docs/margin#adding-space-between-children
       */
      "space-x-reverse": ["space-x-reverse"],
      /**
       * Space Between Y
       * @see https://tailwindcss.com/docs/margin#adding-space-between-children
       */
      "space-y": [{
        "space-y": Y()
      }],
      /**
       * Space Between Y Reverse
       * @see https://tailwindcss.com/docs/margin#adding-space-between-children
       */
      "space-y-reverse": ["space-y-reverse"],
      // --------------
      // --- Sizing ---
      // --------------
      /**
       * Size
       * @see https://tailwindcss.com/docs/width#setting-both-width-and-height
       */
      size: [{
        size: tt()
      }],
      /**
       * Inline Size
       * @see https://tailwindcss.com/docs/inline-size
       */
      "inline-size": [{
        inline: ["auto", ...P()]
      }],
      /**
       * Min-Inline Size
       * @see https://tailwindcss.com/docs/min-inline-size
       */
      "min-inline-size": [{
        "min-inline": ["auto", ...P()]
      }],
      /**
       * Max-Inline Size
       * @see https://tailwindcss.com/docs/max-inline-size
       */
      "max-inline-size": [{
        "max-inline": ["none", ...P()]
      }],
      /**
       * Block Size
       * @see https://tailwindcss.com/docs/block-size
       */
      "block-size": [{
        block: ["auto", ...at()]
      }],
      /**
       * Min-Block Size
       * @see https://tailwindcss.com/docs/min-block-size
       */
      "min-block-size": [{
        "min-block": ["auto", ...at()]
      }],
      /**
       * Max-Block Size
       * @see https://tailwindcss.com/docs/max-block-size
       */
      "max-block-size": [{
        "max-block": ["none", ...at()]
      }],
      /**
       * Width
       * @see https://tailwindcss.com/docs/width
       */
      w: [{
        w: [g, "screen", ...tt()]
      }],
      /**
       * Min-Width
       * @see https://tailwindcss.com/docs/min-width
       */
      "min-w": [{
        "min-w": [
          g,
          "screen",
          /** Deprecated. @see https://github.com/tailwindlabs/tailwindcss.com/issues/2027#issuecomment-2620152757 */
          "none",
          ...tt()
        ]
      }],
      /**
       * Max-Width
       * @see https://tailwindcss.com/docs/max-width
       */
      "max-w": [{
        "max-w": [
          g,
          "screen",
          "none",
          /** Deprecated since Tailwind CSS v4.0.0. @see https://github.com/tailwindlabs/tailwindcss.com/issues/2027#issuecomment-2620152757 */
          "prose",
          /** Deprecated since Tailwind CSS v4.0.0. @see https://github.com/tailwindlabs/tailwindcss.com/issues/2027#issuecomment-2620152757 */
          {
            screen: [v]
          },
          ...tt()
        ]
      }],
      /**
       * Height
       * @see https://tailwindcss.com/docs/height
       */
      h: [{
        h: ["screen", "lh", ...tt()]
      }],
      /**
       * Min-Height
       * @see https://tailwindcss.com/docs/min-height
       */
      "min-h": [{
        "min-h": ["screen", "lh", "none", ...tt()]
      }],
      /**
       * Max-Height
       * @see https://tailwindcss.com/docs/max-height
       */
      "max-h": [{
        "max-h": ["screen", "lh", "none", ...tt()]
      }],
      // ------------------
      // --- Typography ---
      // ------------------
      /**
       * Font Size
       * @see https://tailwindcss.com/docs/font-size
       */
      "font-size": [{
        text: ["base", r, qo, _a]
      }],
      /**
       * Font Smoothing
       * @see https://tailwindcss.com/docs/font-smoothing
       */
      "font-smoothing": ["antialiased", "subpixel-antialiased"],
      /**
       * Font Style
       * @see https://tailwindcss.com/docs/font-style
       */
      "font-style": ["italic", "not-italic"],
      /**
       * Font Weight
       * @see https://tailwindcss.com/docs/font-weight
       */
      "font-weight": [{
        font: [c, I2, Q2]
      }],
      /**
       * Font Stretch
       * @see https://tailwindcss.com/docs/font-stretch
       */
      "font-stretch": [{
        "font-stretch": ["ultra-condensed", "extra-condensed", "condensed", "semi-condensed", "normal", "semi-expanded", "expanded", "extra-expanded", "ultra-expanded", Hf, ot]
      }],
      /**
       * Font Family
       * @see https://tailwindcss.com/docs/font-family
       */
      "font-family": [{
        font: [J2, Z2, u]
      }],
      /**
       * Font Feature Settings
       * @see https://tailwindcss.com/docs/font-feature-settings
       */
      "font-features": [{
        "font-features": [ot]
      }],
      /**
       * Font Variant Numeric
       * @see https://tailwindcss.com/docs/font-variant-numeric
       */
      "fvn-normal": ["normal-nums"],
      /**
       * Font Variant Numeric
       * @see https://tailwindcss.com/docs/font-variant-numeric
       */
      "fvn-ordinal": ["ordinal"],
      /**
       * Font Variant Numeric
       * @see https://tailwindcss.com/docs/font-variant-numeric
       */
      "fvn-slashed-zero": ["slashed-zero"],
      /**
       * Font Variant Numeric
       * @see https://tailwindcss.com/docs/font-variant-numeric
       */
      "fvn-figure": ["lining-nums", "oldstyle-nums"],
      /**
       * Font Variant Numeric
       * @see https://tailwindcss.com/docs/font-variant-numeric
       */
      "fvn-spacing": ["proportional-nums", "tabular-nums"],
      /**
       * Font Variant Numeric
       * @see https://tailwindcss.com/docs/font-variant-numeric
       */
      "fvn-fraction": ["diagonal-fractions", "stacked-fractions"],
      /**
       * Letter Spacing
       * @see https://tailwindcss.com/docs/letter-spacing
       */
      tracking: [{
        tracking: [f, ut, ot]
      }],
      /**
       * Line Clamp
       * @see https://tailwindcss.com/docs/line-clamp
       */
      "line-clamp": [{
        "line-clamp": [_t, "none", ut, S0]
      }],
      /**
       * Line Height
       * @see https://tailwindcss.com/docs/line-height
       */
      leading: [{
        leading: [
          "none",
          /** Deprecated since Tailwind CSS v4.0.0. @see https://github.com/tailwindlabs/tailwindcss.com/issues/2027#issuecomment-2620152757 */
          m,
          ...Y()
        ]
      }],
      /**
       * List Style Image
       * @see https://tailwindcss.com/docs/list-style-image
       */
      "list-image": [{
        "list-image": ["none", ut, ot]
      }],
      /**
       * List Style Position
       * @see https://tailwindcss.com/docs/list-style-position
       */
      "list-style-position": [{
        list: ["inside", "outside"]
      }],
      /**
       * List Style Type
       * @see https://tailwindcss.com/docs/list-style-type
       */
      "list-style-type": [{
        list: ["disc", "decimal", "none", ut, ot]
      }],
      /**
       * Text Alignment
       * @see https://tailwindcss.com/docs/text-align
       */
      "text-alignment": [{
        text: ["left", "center", "right", "justify", "start", "end"]
      }],
      /**
       * Placeholder Color
       * @deprecated since Tailwind CSS v3.0.0
       * @see https://v3.tailwindcss.com/docs/placeholder-color
       */
      "placeholder-color": [{
        placeholder: F()
      }],
      /**
       * Text Color
       * @see https://tailwindcss.com/docs/text-color
       */
      "text-color": [{
        text: F()
      }],
      /**
       * Text Decoration
       * @see https://tailwindcss.com/docs/text-decoration
       */
      "text-decoration": ["underline", "overline", "line-through", "no-underline"],
      /**
       * Text Decoration Style
       * @see https://tailwindcss.com/docs/text-decoration-style
       */
      "text-decoration-style": [{
        decoration: [...$(), "wavy"]
      }],
      /**
       * Text Decoration Thickness
       * @see https://tailwindcss.com/docs/text-decoration-thickness
       */
      "text-decoration-thickness": [{
        decoration: [_t, "from-font", "auto", ut, _a]
      }],
      /**
       * Text Decoration Color
       * @see https://tailwindcss.com/docs/text-decoration-color
       */
      "text-decoration-color": [{
        decoration: F()
      }],
      /**
       * Text Underline Offset
       * @see https://tailwindcss.com/docs/text-underline-offset
       */
      "underline-offset": [{
        "underline-offset": [_t, "auto", ut, ot]
      }],
      /**
       * Text Transform
       * @see https://tailwindcss.com/docs/text-transform
       */
      "text-transform": ["uppercase", "lowercase", "capitalize", "normal-case"],
      /**
       * Text Overflow
       * @see https://tailwindcss.com/docs/text-overflow
       */
      "text-overflow": ["truncate", "text-ellipsis", "text-clip"],
      /**
       * Text Wrap
       * @see https://tailwindcss.com/docs/text-wrap
       */
      "text-wrap": [{
        text: ["wrap", "nowrap", "balance", "pretty"]
      }],
      /**
       * Text Indent
       * @see https://tailwindcss.com/docs/text-indent
       */
      indent: [{
        indent: Y()
      }],
      /**
       * Tab Size
       * @see https://tailwindcss.com/docs/tab-size
       */
      "tab-size": [{
        tab: [Gn, ut, ot]
      }],
      /**
       * Vertical Alignment
       * @see https://tailwindcss.com/docs/vertical-align
       */
      "vertical-align": [{
        align: ["baseline", "top", "middle", "bottom", "text-top", "text-bottom", "sub", "super", ut, ot]
      }],
      /**
       * Whitespace
       * @see https://tailwindcss.com/docs/whitespace
       */
      whitespace: [{
        whitespace: ["normal", "nowrap", "pre", "pre-line", "pre-wrap", "break-spaces"]
      }],
      /**
       * Word Break
       * @see https://tailwindcss.com/docs/word-break
       */
      break: [{
        break: ["normal", "words", "all", "keep"]
      }],
      /**
       * Overflow Wrap
       * @see https://tailwindcss.com/docs/overflow-wrap
       */
      wrap: [{
        wrap: ["break-word", "anywhere", "normal"]
      }],
      /**
       * Hyphens
       * @see https://tailwindcss.com/docs/hyphens
       */
      hyphens: [{
        hyphens: ["none", "manual", "auto"]
      }],
      /**
       * Content
       * @see https://tailwindcss.com/docs/content
       */
      content: [{
        content: ["none", ut, ot]
      }],
      // -------------------
      // --- Backgrounds ---
      // -------------------
      /**
       * Background Attachment
       * @see https://tailwindcss.com/docs/background-attachment
       */
      "bg-attachment": [{
        bg: ["fixed", "local", "scroll"]
      }],
      /**
       * Background Clip
       * @see https://tailwindcss.com/docs/background-clip
       */
      "bg-clip": [{
        "bg-clip": ["border", "padding", "content", "text"]
      }],
      /**
       * Background Origin
       * @see https://tailwindcss.com/docs/background-origin
       */
      "bg-origin": [{
        "bg-origin": ["border", "padding", "content"]
      }],
      /**
       * Background Position
       * @see https://tailwindcss.com/docs/background-position
       */
      "bg-position": [{
        bg: Bt()
      }],
      /**
       * Background Repeat
       * @see https://tailwindcss.com/docs/background-repeat
       */
      "bg-repeat": [{
        bg: Q()
      }],
      /**
       * Background Size
       * @see https://tailwindcss.com/docs/background-size
       */
      "bg-size": [{
        bg: rt()
      }],
      /**
       * Background Image
       * @see https://tailwindcss.com/docs/background-image
       */
      "bg-image": [{
        bg: ["none", {
          linear: [{
            to: ["t", "tr", "r", "br", "b", "bl", "l", "tl"]
          }, Gn, ut, ot],
          radial: ["", ut, ot],
          conic: ["", Gn, ut, ot]
        }, $2, K2]
      }],
      /**
       * Background Color
       * @see https://tailwindcss.com/docs/background-color
       */
      "bg-color": [{
        bg: F()
      }],
      /**
       * Gradient Color Stops From Position
       * @see https://tailwindcss.com/docs/gradient-color-stops
       */
      "gradient-from-pos": [{
        from: E()
      }],
      /**
       * Gradient Color Stops Via Position
       * @see https://tailwindcss.com/docs/gradient-color-stops
       */
      "gradient-via-pos": [{
        via: E()
      }],
      /**
       * Gradient Color Stops To Position
       * @see https://tailwindcss.com/docs/gradient-color-stops
       */
      "gradient-to-pos": [{
        to: E()
      }],
      /**
       * Gradient Color Stops From
       * @see https://tailwindcss.com/docs/gradient-color-stops
       */
      "gradient-from": [{
        from: F()
      }],
      /**
       * Gradient Color Stops Via
       * @see https://tailwindcss.com/docs/gradient-color-stops
       */
      "gradient-via": [{
        via: F()
      }],
      /**
       * Gradient Color Stops To
       * @see https://tailwindcss.com/docs/gradient-color-stops
       */
      "gradient-to": [{
        to: F()
      }],
      // ---------------
      // --- Borders ---
      // ---------------
      /**
       * Border Radius
       * @see https://tailwindcss.com/docs/border-radius
       */
      rounded: [{
        rounded: _()
      }],
      /**
       * Border Radius Start
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-s": [{
        "rounded-s": _()
      }],
      /**
       * Border Radius End
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-e": [{
        "rounded-e": _()
      }],
      /**
       * Border Radius Top
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-t": [{
        "rounded-t": _()
      }],
      /**
       * Border Radius Right
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-r": [{
        "rounded-r": _()
      }],
      /**
       * Border Radius Bottom
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-b": [{
        "rounded-b": _()
      }],
      /**
       * Border Radius Left
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-l": [{
        "rounded-l": _()
      }],
      /**
       * Border Radius Start Start
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-ss": [{
        "rounded-ss": _()
      }],
      /**
       * Border Radius Start End
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-se": [{
        "rounded-se": _()
      }],
      /**
       * Border Radius End End
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-ee": [{
        "rounded-ee": _()
      }],
      /**
       * Border Radius End Start
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-es": [{
        "rounded-es": _()
      }],
      /**
       * Border Radius Top Left
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-tl": [{
        "rounded-tl": _()
      }],
      /**
       * Border Radius Top Right
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-tr": [{
        "rounded-tr": _()
      }],
      /**
       * Border Radius Bottom Right
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-br": [{
        "rounded-br": _()
      }],
      /**
       * Border Radius Bottom Left
       * @see https://tailwindcss.com/docs/border-radius
       */
      "rounded-bl": [{
        "rounded-bl": _()
      }],
      /**
       * Border Width
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w": [{
        border: V()
      }],
      /**
       * Border Width Inline
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-x": [{
        "border-x": V()
      }],
      /**
       * Border Width Block
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-y": [{
        "border-y": V()
      }],
      /**
       * Border Width Inline Start
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-s": [{
        "border-s": V()
      }],
      /**
       * Border Width Inline End
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-e": [{
        "border-e": V()
      }],
      /**
       * Border Width Block Start
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-bs": [{
        "border-bs": V()
      }],
      /**
       * Border Width Block End
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-be": [{
        "border-be": V()
      }],
      /**
       * Border Width Top
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-t": [{
        "border-t": V()
      }],
      /**
       * Border Width Right
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-r": [{
        "border-r": V()
      }],
      /**
       * Border Width Bottom
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-b": [{
        "border-b": V()
      }],
      /**
       * Border Width Left
       * @see https://tailwindcss.com/docs/border-width
       */
      "border-w-l": [{
        "border-l": V()
      }],
      /**
       * Divide Width X
       * @see https://tailwindcss.com/docs/border-width#between-children
       */
      "divide-x": [{
        "divide-x": V()
      }],
      /**
       * Divide Width X Reverse
       * @see https://tailwindcss.com/docs/border-width#between-children
       */
      "divide-x-reverse": ["divide-x-reverse"],
      /**
       * Divide Width Y
       * @see https://tailwindcss.com/docs/border-width#between-children
       */
      "divide-y": [{
        "divide-y": V()
      }],
      /**
       * Divide Width Y Reverse
       * @see https://tailwindcss.com/docs/border-width#between-children
       */
      "divide-y-reverse": ["divide-y-reverse"],
      /**
       * Border Style
       * @see https://tailwindcss.com/docs/border-style
       */
      "border-style": [{
        border: [...$(), "hidden", "none"]
      }],
      /**
       * Divide Style
       * @see https://tailwindcss.com/docs/border-style#setting-the-divider-style
       */
      "divide-style": [{
        divide: [...$(), "hidden", "none"]
      }],
      /**
       * Border Color
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color": [{
        border: F()
      }],
      /**
       * Border Color Inline
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-x": [{
        "border-x": F()
      }],
      /**
       * Border Color Block
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-y": [{
        "border-y": F()
      }],
      /**
       * Border Color Inline Start
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-s": [{
        "border-s": F()
      }],
      /**
       * Border Color Inline End
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-e": [{
        "border-e": F()
      }],
      /**
       * Border Color Block Start
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-bs": [{
        "border-bs": F()
      }],
      /**
       * Border Color Block End
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-be": [{
        "border-be": F()
      }],
      /**
       * Border Color Top
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-t": [{
        "border-t": F()
      }],
      /**
       * Border Color Right
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-r": [{
        "border-r": F()
      }],
      /**
       * Border Color Bottom
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-b": [{
        "border-b": F()
      }],
      /**
       * Border Color Left
       * @see https://tailwindcss.com/docs/border-color
       */
      "border-color-l": [{
        "border-l": F()
      }],
      /**
       * Divide Color
       * @see https://tailwindcss.com/docs/divide-color
       */
      "divide-color": [{
        divide: F()
      }],
      /**
       * Outline Style
       * @see https://tailwindcss.com/docs/outline-style
       */
      "outline-style": [{
        outline: [...$(), "none", "hidden"]
      }],
      /**
       * Outline Offset
       * @see https://tailwindcss.com/docs/outline-offset
       */
      "outline-offset": [{
        "outline-offset": [_t, ut, ot]
      }],
      /**
       * Outline Width
       * @see https://tailwindcss.com/docs/outline-width
       */
      "outline-w": [{
        outline: ["", _t, qo, _a]
      }],
      /**
       * Outline Color
       * @see https://tailwindcss.com/docs/outline-color
       */
      "outline-color": [{
        outline: F()
      }],
      // ---------------
      // --- Effects ---
      // ---------------
      /**
       * Box Shadow
       * @see https://tailwindcss.com/docs/box-shadow
       */
      shadow: [{
        shadow: [
          // Deprecated since Tailwind CSS v4.0.0
          "",
          // Deprecated since Tailwind CSS v4.0.0
          "inner",
          "none",
          S,
          Ar,
          _r
        ]
      }],
      /**
       * Box Shadow Color
       * @see https://tailwindcss.com/docs/box-shadow#setting-the-shadow-color
       */
      "shadow-color": [{
        shadow: F()
      }],
      /**
       * Inset Box Shadow
       * @see https://tailwindcss.com/docs/box-shadow#adding-an-inset-shadow
       */
      "inset-shadow": [{
        "inset-shadow": ["none", d, Ar, _r]
      }],
      /**
       * Inset Box Shadow Color
       * @see https://tailwindcss.com/docs/box-shadow#setting-the-inset-shadow-color
       */
      "inset-shadow-color": [{
        "inset-shadow": F()
      }],
      /**
       * Ring Width
       * @see https://tailwindcss.com/docs/box-shadow#adding-a-ring
       */
      "ring-w": [{
        ring: V()
      }],
      /**
       * Ring Width Inset
       * @see https://v3.tailwindcss.com/docs/ring-width#inset-rings
       * @deprecated since Tailwind CSS v4.0.0
       * @see https://github.com/tailwindlabs/tailwindcss/blob/v4.0.0/packages/tailwindcss/src/utilities.ts#L4158
       */
      "ring-w-inset": ["ring-inset"],
      /**
       * Ring Color
       * @see https://tailwindcss.com/docs/box-shadow#setting-the-ring-color
       */
      "ring-color": [{
        ring: F()
      }],
      /**
       * Ring Offset Width
       * @see https://v3.tailwindcss.com/docs/ring-offset-width
       * @deprecated since Tailwind CSS v4.0.0
       * @see https://github.com/tailwindlabs/tailwindcss/blob/v4.0.0/packages/tailwindcss/src/utilities.ts#L4158
       */
      "ring-offset-w": [{
        "ring-offset": [_t, _a]
      }],
      /**
       * Ring Offset Color
       * @see https://v3.tailwindcss.com/docs/ring-offset-color
       * @deprecated since Tailwind CSS v4.0.0
       * @see https://github.com/tailwindlabs/tailwindcss/blob/v4.0.0/packages/tailwindcss/src/utilities.ts#L4158
       */
      "ring-offset-color": [{
        "ring-offset": F()
      }],
      /**
       * Inset Ring Width
       * @see https://tailwindcss.com/docs/box-shadow#adding-an-inset-ring
       */
      "inset-ring-w": [{
        "inset-ring": V()
      }],
      /**
       * Inset Ring Color
       * @see https://tailwindcss.com/docs/box-shadow#setting-the-inset-ring-color
       */
      "inset-ring-color": [{
        "inset-ring": F()
      }],
      /**
       * Text Shadow
       * @see https://tailwindcss.com/docs/text-shadow
       */
      "text-shadow": [{
        "text-shadow": ["none", x, Ar, _r]
      }],
      /**
       * Text Shadow Color
       * @see https://tailwindcss.com/docs/text-shadow#setting-the-shadow-color
       */
      "text-shadow-color": [{
        "text-shadow": F()
      }],
      /**
       * Opacity
       * @see https://tailwindcss.com/docs/opacity
       */
      opacity: [{
        opacity: [_t, ut, ot]
      }],
      /**
       * Mix Blend Mode
       * @see https://tailwindcss.com/docs/mix-blend-mode
       */
      "mix-blend": [{
        "mix-blend": [...ft(), "plus-darker", "plus-lighter"]
      }],
      /**
       * Background Blend Mode
       * @see https://tailwindcss.com/docs/background-blend-mode
       */
      "bg-blend": [{
        "bg-blend": ft()
      }],
      /**
       * Mask Clip
       * @see https://tailwindcss.com/docs/mask-clip
       */
      "mask-clip": [{
        "mask-clip": ["border", "padding", "content", "fill", "stroke", "view"]
      }, "mask-no-clip"],
      /**
       * Mask Composite
       * @see https://tailwindcss.com/docs/mask-composite
       */
      "mask-composite": [{
        mask: ["add", "subtract", "intersect", "exclude"]
      }],
      /**
       * Mask Image
       * @see https://tailwindcss.com/docs/mask-image
       */
      "mask-image-linear-pos": [{
        "mask-linear": [_t]
      }],
      "mask-image-linear-from-pos": [{
        "mask-linear-from": W()
      }],
      "mask-image-linear-to-pos": [{
        "mask-linear-to": W()
      }],
      "mask-image-linear-from-color": [{
        "mask-linear-from": F()
      }],
      "mask-image-linear-to-color": [{
        "mask-linear-to": F()
      }],
      "mask-image-t-from-pos": [{
        "mask-t-from": W()
      }],
      "mask-image-t-to-pos": [{
        "mask-t-to": W()
      }],
      "mask-image-t-from-color": [{
        "mask-t-from": F()
      }],
      "mask-image-t-to-color": [{
        "mask-t-to": F()
      }],
      "mask-image-r-from-pos": [{
        "mask-r-from": W()
      }],
      "mask-image-r-to-pos": [{
        "mask-r-to": W()
      }],
      "mask-image-r-from-color": [{
        "mask-r-from": F()
      }],
      "mask-image-r-to-color": [{
        "mask-r-to": F()
      }],
      "mask-image-b-from-pos": [{
        "mask-b-from": W()
      }],
      "mask-image-b-to-pos": [{
        "mask-b-to": W()
      }],
      "mask-image-b-from-color": [{
        "mask-b-from": F()
      }],
      "mask-image-b-to-color": [{
        "mask-b-to": F()
      }],
      "mask-image-l-from-pos": [{
        "mask-l-from": W()
      }],
      "mask-image-l-to-pos": [{
        "mask-l-to": W()
      }],
      "mask-image-l-from-color": [{
        "mask-l-from": F()
      }],
      "mask-image-l-to-color": [{
        "mask-l-to": F()
      }],
      "mask-image-x-from-pos": [{
        "mask-x-from": W()
      }],
      "mask-image-x-to-pos": [{
        "mask-x-to": W()
      }],
      "mask-image-x-from-color": [{
        "mask-x-from": F()
      }],
      "mask-image-x-to-color": [{
        "mask-x-to": F()
      }],
      "mask-image-y-from-pos": [{
        "mask-y-from": W()
      }],
      "mask-image-y-to-pos": [{
        "mask-y-to": W()
      }],
      "mask-image-y-from-color": [{
        "mask-y-from": F()
      }],
      "mask-image-y-to-color": [{
        "mask-y-to": F()
      }],
      "mask-image-radial": [{
        "mask-radial": [ut, ot]
      }],
      "mask-image-radial-from-pos": [{
        "mask-radial-from": W()
      }],
      "mask-image-radial-to-pos": [{
        "mask-radial-to": W()
      }],
      "mask-image-radial-from-color": [{
        "mask-radial-from": F()
      }],
      "mask-image-radial-to-color": [{
        "mask-radial-to": F()
      }],
      "mask-image-radial-shape": [{
        "mask-radial": ["circle", "ellipse"]
      }],
      "mask-image-radial-size": [{
        "mask-radial": [{
          closest: ["side", "corner"],
          farthest: ["side", "corner"]
        }]
      }],
      "mask-image-radial-pos": [{
        "mask-radial-at": K()
      }],
      "mask-image-conic-pos": [{
        "mask-conic": [_t]
      }],
      "mask-image-conic-from-pos": [{
        "mask-conic-from": W()
      }],
      "mask-image-conic-to-pos": [{
        "mask-conic-to": W()
      }],
      "mask-image-conic-from-color": [{
        "mask-conic-from": F()
      }],
      "mask-image-conic-to-color": [{
        "mask-conic-to": F()
      }],
      /**
       * Mask Mode
       * @see https://tailwindcss.com/docs/mask-mode
       */
      "mask-mode": [{
        mask: ["alpha", "luminance", "match"]
      }],
      /**
       * Mask Origin
       * @see https://tailwindcss.com/docs/mask-origin
       */
      "mask-origin": [{
        "mask-origin": ["border", "padding", "content", "fill", "stroke", "view"]
      }],
      /**
       * Mask Position
       * @see https://tailwindcss.com/docs/mask-position
       */
      "mask-position": [{
        mask: Bt()
      }],
      /**
       * Mask Repeat
       * @see https://tailwindcss.com/docs/mask-repeat
       */
      "mask-repeat": [{
        mask: Q()
      }],
      /**
       * Mask Size
       * @see https://tailwindcss.com/docs/mask-size
       */
      "mask-size": [{
        mask: rt()
      }],
      /**
       * Mask Type
       * @see https://tailwindcss.com/docs/mask-type
       */
      "mask-type": [{
        "mask-type": ["alpha", "luminance"]
      }],
      /**
       * Mask Image
       * @see https://tailwindcss.com/docs/mask-image
       */
      "mask-image": [{
        mask: ["none", ut, ot]
      }],
      // ---------------
      // --- Filters ---
      // ---------------
      /**
       * Filter
       * @see https://tailwindcss.com/docs/filter
       */
      filter: [{
        filter: [
          // Deprecated since Tailwind CSS v3.0.0
          "",
          "none",
          ut,
          ot
        ]
      }],
      /**
       * Blur
       * @see https://tailwindcss.com/docs/blur
       */
      blur: [{
        blur: bt()
      }],
      /**
       * Brightness
       * @see https://tailwindcss.com/docs/brightness
       */
      brightness: [{
        brightness: [_t, ut, ot]
      }],
      /**
       * Contrast
       * @see https://tailwindcss.com/docs/contrast
       */
      contrast: [{
        contrast: [_t, ut, ot]
      }],
      /**
       * Drop Shadow
       * @see https://tailwindcss.com/docs/drop-shadow
       */
      "drop-shadow": [{
        "drop-shadow": [
          // Deprecated since Tailwind CSS v4.0.0
          "",
          "none",
          C,
          Ar,
          _r
        ]
      }],
      /**
       * Drop Shadow Color
       * @see https://tailwindcss.com/docs/filter-drop-shadow#setting-the-shadow-color
       */
      "drop-shadow-color": [{
        "drop-shadow": F()
      }],
      /**
       * Grayscale
       * @see https://tailwindcss.com/docs/grayscale
       */
      grayscale: [{
        grayscale: ["", _t, ut, ot]
      }],
      /**
       * Hue Rotate
       * @see https://tailwindcss.com/docs/hue-rotate
       */
      "hue-rotate": [{
        "hue-rotate": [_t, ut, ot]
      }],
      /**
       * Invert
       * @see https://tailwindcss.com/docs/invert
       */
      invert: [{
        invert: ["", _t, ut, ot]
      }],
      /**
       * Saturate
       * @see https://tailwindcss.com/docs/saturate
       */
      saturate: [{
        saturate: [_t, ut, ot]
      }],
      /**
       * Sepia
       * @see https://tailwindcss.com/docs/sepia
       */
      sepia: [{
        sepia: ["", _t, ut, ot]
      }],
      /**
       * Backdrop Filter
       * @see https://tailwindcss.com/docs/backdrop-filter
       */
      "backdrop-filter": [{
        "backdrop-filter": [
          // Deprecated since Tailwind CSS v3.0.0
          "",
          "none",
          ut,
          ot
        ]
      }],
      /**
       * Backdrop Blur
       * @see https://tailwindcss.com/docs/backdrop-blur
       */
      "backdrop-blur": [{
        "backdrop-blur": bt()
      }],
      /**
       * Backdrop Brightness
       * @see https://tailwindcss.com/docs/backdrop-brightness
       */
      "backdrop-brightness": [{
        "backdrop-brightness": [_t, ut, ot]
      }],
      /**
       * Backdrop Contrast
       * @see https://tailwindcss.com/docs/backdrop-contrast
       */
      "backdrop-contrast": [{
        "backdrop-contrast": [_t, ut, ot]
      }],
      /**
       * Backdrop Grayscale
       * @see https://tailwindcss.com/docs/backdrop-grayscale
       */
      "backdrop-grayscale": [{
        "backdrop-grayscale": ["", _t, ut, ot]
      }],
      /**
       * Backdrop Hue Rotate
       * @see https://tailwindcss.com/docs/backdrop-hue-rotate
       */
      "backdrop-hue-rotate": [{
        "backdrop-hue-rotate": [_t, ut, ot]
      }],
      /**
       * Backdrop Invert
       * @see https://tailwindcss.com/docs/backdrop-invert
       */
      "backdrop-invert": [{
        "backdrop-invert": ["", _t, ut, ot]
      }],
      /**
       * Backdrop Opacity
       * @see https://tailwindcss.com/docs/backdrop-opacity
       */
      "backdrop-opacity": [{
        "backdrop-opacity": [_t, ut, ot]
      }],
      /**
       * Backdrop Saturate
       * @see https://tailwindcss.com/docs/backdrop-saturate
       */
      "backdrop-saturate": [{
        "backdrop-saturate": [_t, ut, ot]
      }],
      /**
       * Backdrop Sepia
       * @see https://tailwindcss.com/docs/backdrop-sepia
       */
      "backdrop-sepia": [{
        "backdrop-sepia": ["", _t, ut, ot]
      }],
      // --------------
      // --- Tables ---
      // --------------
      /**
       * Border Collapse
       * @see https://tailwindcss.com/docs/border-collapse
       */
      "border-collapse": [{
        border: ["collapse", "separate"]
      }],
      /**
       * Border Spacing
       * @see https://tailwindcss.com/docs/border-spacing
       */
      "border-spacing": [{
        "border-spacing": Y()
      }],
      /**
       * Border Spacing X
       * @see https://tailwindcss.com/docs/border-spacing
       */
      "border-spacing-x": [{
        "border-spacing-x": Y()
      }],
      /**
       * Border Spacing Y
       * @see https://tailwindcss.com/docs/border-spacing
       */
      "border-spacing-y": [{
        "border-spacing-y": Y()
      }],
      /**
       * Table Layout
       * @see https://tailwindcss.com/docs/table-layout
       */
      "table-layout": [{
        table: ["auto", "fixed"]
      }],
      /**
       * Caption Side
       * @see https://tailwindcss.com/docs/caption-side
       */
      caption: [{
        caption: ["top", "bottom"]
      }],
      // ---------------------------------
      // --- Transitions and Animation ---
      // ---------------------------------
      /**
       * Transition Property
       * @see https://tailwindcss.com/docs/transition-property
       */
      transition: [{
        transition: ["", "all", "colors", "opacity", "shadow", "transform", "none", ut, ot]
      }],
      /**
       * Transition Behavior
       * @see https://tailwindcss.com/docs/transition-behavior
       */
      "transition-behavior": [{
        transition: ["normal", "discrete"]
      }],
      /**
       * Transition Duration
       * @see https://tailwindcss.com/docs/transition-duration
       */
      duration: [{
        duration: [_t, "initial", ut, ot]
      }],
      /**
       * Transition Timing Function
       * @see https://tailwindcss.com/docs/transition-timing-function
       */
      ease: [{
        ease: ["linear", "initial", H, ut, ot]
      }],
      /**
       * Transition Delay
       * @see https://tailwindcss.com/docs/transition-delay
       */
      delay: [{
        delay: [_t, ut, ot]
      }],
      /**
       * Animation
       * @see https://tailwindcss.com/docs/animation
       */
      animate: [{
        animate: ["none", L, ut, ot]
      }],
      // ------------------
      // --- Transforms ---
      // ------------------
      /**
       * Backface Visibility
       * @see https://tailwindcss.com/docs/backface-visibility
       */
      backface: [{
        backface: ["hidden", "visible"]
      }],
      /**
       * Perspective
       * @see https://tailwindcss.com/docs/perspective
       */
      perspective: [{
        perspective: [O, ut, ot]
      }],
      /**
       * Perspective Origin
       * @see https://tailwindcss.com/docs/perspective-origin
       */
      "perspective-origin": [{
        "perspective-origin": I()
      }],
      /**
       * Rotate
       * @see https://tailwindcss.com/docs/rotate
       */
      rotate: [{
        rotate: lt()
      }],
      /**
       * Rotate X
       * @see https://tailwindcss.com/docs/rotate
       */
      "rotate-x": [{
        "rotate-x": lt()
      }],
      /**
       * Rotate Y
       * @see https://tailwindcss.com/docs/rotate
       */
      "rotate-y": [{
        "rotate-y": lt()
      }],
      /**
       * Rotate Z
       * @see https://tailwindcss.com/docs/rotate
       */
      "rotate-z": [{
        "rotate-z": lt()
      }],
      /**
       * Scale
       * @see https://tailwindcss.com/docs/scale
       */
      scale: [{
        scale: mt()
      }],
      /**
       * Scale X
       * @see https://tailwindcss.com/docs/scale
       */
      "scale-x": [{
        "scale-x": mt()
      }],
      /**
       * Scale Y
       * @see https://tailwindcss.com/docs/scale
       */
      "scale-y": [{
        "scale-y": mt()
      }],
      /**
       * Scale Z
       * @see https://tailwindcss.com/docs/scale
       */
      "scale-z": [{
        "scale-z": mt()
      }],
      /**
       * Scale 3D
       * @see https://tailwindcss.com/docs/scale
       */
      "scale-3d": ["scale-3d"],
      /**
       * Skew
       * @see https://tailwindcss.com/docs/skew
       */
      skew: [{
        skew: It()
      }],
      /**
       * Skew X
       * @see https://tailwindcss.com/docs/skew
       */
      "skew-x": [{
        "skew-x": It()
      }],
      /**
       * Skew Y
       * @see https://tailwindcss.com/docs/skew
       */
      "skew-y": [{
        "skew-y": It()
      }],
      /**
       * Transform
       * @see https://tailwindcss.com/docs/transform
       */
      transform: [{
        transform: [ut, ot, "", "none", "gpu", "cpu"]
      }],
      /**
       * Transform Origin
       * @see https://tailwindcss.com/docs/transform-origin
       */
      "transform-origin": [{
        origin: I()
      }],
      /**
       * Transform Style
       * @see https://tailwindcss.com/docs/transform-style
       */
      "transform-style": [{
        transform: ["3d", "flat"]
      }],
      /**
       * Translate
       * @see https://tailwindcss.com/docs/translate
       */
      translate: [{
        translate: _e()
      }],
      /**
       * Translate X
       * @see https://tailwindcss.com/docs/translate
       */
      "translate-x": [{
        "translate-x": _e()
      }],
      /**
       * Translate Y
       * @see https://tailwindcss.com/docs/translate
       */
      "translate-y": [{
        "translate-y": _e()
      }],
      /**
       * Translate Z
       * @see https://tailwindcss.com/docs/translate
       */
      "translate-z": [{
        "translate-z": _e()
      }],
      /**
       * Translate None
       * @see https://tailwindcss.com/docs/translate
       */
      "translate-none": ["translate-none"],
      /**
       * Zoom
       * @see https://tailwindcss.com/docs/zoom
       */
      zoom: [{
        zoom: [Gn, ut, ot]
      }],
      // ---------------------
      // --- Interactivity ---
      // ---------------------
      /**
       * Accent Color
       * @see https://tailwindcss.com/docs/accent-color
       */
      accent: [{
        accent: F()
      }],
      /**
       * Appearance
       * @see https://tailwindcss.com/docs/appearance
       */
      appearance: [{
        appearance: ["none", "auto"]
      }],
      /**
       * Caret Color
       * @see https://tailwindcss.com/docs/just-in-time-mode#caret-color-utilities
       */
      "caret-color": [{
        caret: F()
      }],
      /**
       * Color Scheme
       * @see https://tailwindcss.com/docs/color-scheme
       */
      "color-scheme": [{
        scheme: ["normal", "dark", "light", "light-dark", "only-dark", "only-light"]
      }],
      /**
       * Cursor
       * @see https://tailwindcss.com/docs/cursor
       */
      cursor: [{
        cursor: ["auto", "default", "pointer", "wait", "text", "move", "help", "not-allowed", "none", "context-menu", "progress", "cell", "crosshair", "vertical-text", "alias", "copy", "no-drop", "grab", "grabbing", "all-scroll", "col-resize", "row-resize", "n-resize", "e-resize", "s-resize", "w-resize", "ne-resize", "nw-resize", "se-resize", "sw-resize", "ew-resize", "ns-resize", "nesw-resize", "nwse-resize", "zoom-in", "zoom-out", ut, ot]
      }],
      /**
       * Field Sizing
       * @see https://tailwindcss.com/docs/field-sizing
       */
      "field-sizing": [{
        "field-sizing": ["fixed", "content"]
      }],
      /**
       * Pointer Events
       * @see https://tailwindcss.com/docs/pointer-events
       */
      "pointer-events": [{
        "pointer-events": ["auto", "none"]
      }],
      /**
       * Resize
       * @see https://tailwindcss.com/docs/resize
       */
      resize: [{
        resize: ["none", "", "y", "x"]
      }],
      /**
       * Scroll Behavior
       * @see https://tailwindcss.com/docs/scroll-behavior
       */
      "scroll-behavior": [{
        scroll: ["auto", "smooth"]
      }],
      /**
       * Scrollbar Thumb Color
       * @see https://tailwindcss.com/docs/scrollbar-color
       */
      "scrollbar-thumb-color": [{
        "scrollbar-thumb": F()
      }],
      /**
       * Scrollbar Track Color
       * @see https://tailwindcss.com/docs/scrollbar-color
       */
      "scrollbar-track-color": [{
        "scrollbar-track": F()
      }],
      /**
       * Scrollbar Gutter
       * @see https://tailwindcss.com/docs/scrollbar-gutter
       */
      "scrollbar-gutter": [{
        "scrollbar-gutter": ["auto", "stable", "both"]
      }],
      /**
       * Scrollbar Width
       * @see https://tailwindcss.com/docs/scrollbar-width
       */
      "scrollbar-w": [{
        scrollbar: ["auto", "thin", "none"]
      }],
      /**
       * Scroll Margin
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-m": [{
        "scroll-m": Y()
      }],
      /**
       * Scroll Margin Inline
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-mx": [{
        "scroll-mx": Y()
      }],
      /**
       * Scroll Margin Block
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-my": [{
        "scroll-my": Y()
      }],
      /**
       * Scroll Margin Inline Start
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-ms": [{
        "scroll-ms": Y()
      }],
      /**
       * Scroll Margin Inline End
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-me": [{
        "scroll-me": Y()
      }],
      /**
       * Scroll Margin Block Start
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-mbs": [{
        "scroll-mbs": Y()
      }],
      /**
       * Scroll Margin Block End
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-mbe": [{
        "scroll-mbe": Y()
      }],
      /**
       * Scroll Margin Top
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-mt": [{
        "scroll-mt": Y()
      }],
      /**
       * Scroll Margin Right
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-mr": [{
        "scroll-mr": Y()
      }],
      /**
       * Scroll Margin Bottom
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-mb": [{
        "scroll-mb": Y()
      }],
      /**
       * Scroll Margin Left
       * @see https://tailwindcss.com/docs/scroll-margin
       */
      "scroll-ml": [{
        "scroll-ml": Y()
      }],
      /**
       * Scroll Padding
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-p": [{
        "scroll-p": Y()
      }],
      /**
       * Scroll Padding Inline
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-px": [{
        "scroll-px": Y()
      }],
      /**
       * Scroll Padding Block
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-py": [{
        "scroll-py": Y()
      }],
      /**
       * Scroll Padding Inline Start
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-ps": [{
        "scroll-ps": Y()
      }],
      /**
       * Scroll Padding Inline End
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pe": [{
        "scroll-pe": Y()
      }],
      /**
       * Scroll Padding Block Start
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pbs": [{
        "scroll-pbs": Y()
      }],
      /**
       * Scroll Padding Block End
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pbe": [{
        "scroll-pbe": Y()
      }],
      /**
       * Scroll Padding Top
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pt": [{
        "scroll-pt": Y()
      }],
      /**
       * Scroll Padding Right
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pr": [{
        "scroll-pr": Y()
      }],
      /**
       * Scroll Padding Bottom
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pb": [{
        "scroll-pb": Y()
      }],
      /**
       * Scroll Padding Left
       * @see https://tailwindcss.com/docs/scroll-padding
       */
      "scroll-pl": [{
        "scroll-pl": Y()
      }],
      /**
       * Scroll Snap Align
       * @see https://tailwindcss.com/docs/scroll-snap-align
       */
      "snap-align": [{
        snap: ["start", "end", "center", "align-none"]
      }],
      /**
       * Scroll Snap Stop
       * @see https://tailwindcss.com/docs/scroll-snap-stop
       */
      "snap-stop": [{
        snap: ["normal", "always"]
      }],
      /**
       * Scroll Snap Type
       * @see https://tailwindcss.com/docs/scroll-snap-type
       */
      "snap-type": [{
        snap: ["none", "x", "y", "both"]
      }],
      /**
       * Scroll Snap Type Strictness
       * @see https://tailwindcss.com/docs/scroll-snap-type
       */
      "snap-strictness": [{
        snap: ["mandatory", "proximity"]
      }],
      /**
       * Touch Action
       * @see https://tailwindcss.com/docs/touch-action
       */
      touch: [{
        touch: ["auto", "none", "manipulation"]
      }],
      /**
       * Touch Action X
       * @see https://tailwindcss.com/docs/touch-action
       */
      "touch-x": [{
        "touch-pan": ["x", "left", "right"]
      }],
      /**
       * Touch Action Y
       * @see https://tailwindcss.com/docs/touch-action
       */
      "touch-y": [{
        "touch-pan": ["y", "up", "down"]
      }],
      /**
       * Touch Action Pinch Zoom
       * @see https://tailwindcss.com/docs/touch-action
       */
      "touch-pz": ["touch-pinch-zoom"],
      /**
       * User Select
       * @see https://tailwindcss.com/docs/user-select
       */
      select: [{
        select: ["none", "text", "all", "auto"]
      }],
      /**
       * Will Change
       * @see https://tailwindcss.com/docs/will-change
       */
      "will-change": [{
        "will-change": ["auto", "scroll", "contents", "transform", ut, ot]
      }],
      // -----------
      // --- SVG ---
      // -----------
      /**
       * Fill
       * @see https://tailwindcss.com/docs/fill
       */
      fill: [{
        fill: ["none", ...F()]
      }],
      /**
       * Stroke Width
       * @see https://tailwindcss.com/docs/stroke-width
       */
      "stroke-w": [{
        stroke: [_t, qo, _a, S0]
      }],
      /**
       * Stroke
       * @see https://tailwindcss.com/docs/stroke
       */
      stroke: [{
        stroke: ["none", ...F()]
      }],
      // ---------------------
      // --- Accessibility ---
      // ---------------------
      /**
       * Forced Color Adjust
       * @see https://tailwindcss.com/docs/forced-color-adjust
       */
      "forced-color-adjust": [{
        "forced-color-adjust": ["auto", "none"]
      }]
    },
    conflictingClassGroups: {
      "container-named": ["container-type"],
      overflow: ["overflow-x", "overflow-y"],
      overscroll: ["overscroll-x", "overscroll-y"],
      inset: ["inset-x", "inset-y", "inset-bs", "inset-be", "start", "end", "top", "right", "bottom", "left"],
      "inset-x": ["start", "end", "right", "left"],
      "inset-y": ["inset-bs", "inset-be", "top", "bottom"],
      flex: ["basis", "grow", "shrink"],
      gap: ["gap-x", "gap-y"],
      p: ["px", "py", "ps", "pe", "pbs", "pbe", "pt", "pr", "pb", "pl"],
      px: ["ps", "pe", "pr", "pl"],
      py: ["pbs", "pbe", "pt", "pb"],
      m: ["mx", "my", "ms", "me", "mbs", "mbe", "mt", "mr", "mb", "ml"],
      mx: ["ms", "me", "mr", "ml"],
      my: ["mbs", "mbe", "mt", "mb"],
      size: ["w", "h"],
      "font-size": ["leading"],
      "fvn-normal": ["fvn-ordinal", "fvn-slashed-zero", "fvn-figure", "fvn-spacing", "fvn-fraction"],
      "fvn-ordinal": ["fvn-normal"],
      "fvn-slashed-zero": ["fvn-normal"],
      "fvn-figure": ["fvn-normal"],
      "fvn-spacing": ["fvn-normal"],
      "fvn-fraction": ["fvn-normal"],
      "line-clamp": ["display", "overflow"],
      rounded: ["rounded-s", "rounded-e", "rounded-t", "rounded-r", "rounded-b", "rounded-l", "rounded-ss", "rounded-se", "rounded-ee", "rounded-es", "rounded-tl", "rounded-tr", "rounded-br", "rounded-bl"],
      "rounded-s": ["rounded-ss", "rounded-es"],
      "rounded-e": ["rounded-se", "rounded-ee"],
      "rounded-t": ["rounded-tl", "rounded-tr"],
      "rounded-r": ["rounded-tr", "rounded-br"],
      "rounded-b": ["rounded-br", "rounded-bl"],
      "rounded-l": ["rounded-tl", "rounded-bl"],
      "border-spacing": ["border-spacing-x", "border-spacing-y"],
      "border-w": ["border-w-x", "border-w-y", "border-w-s", "border-w-e", "border-w-bs", "border-w-be", "border-w-t", "border-w-r", "border-w-b", "border-w-l"],
      "border-w-x": ["border-w-s", "border-w-e", "border-w-r", "border-w-l"],
      "border-w-y": ["border-w-bs", "border-w-be", "border-w-t", "border-w-b"],
      "border-color": ["border-color-x", "border-color-y", "border-color-s", "border-color-e", "border-color-bs", "border-color-be", "border-color-t", "border-color-r", "border-color-b", "border-color-l"],
      "border-color-x": ["border-color-s", "border-color-e", "border-color-r", "border-color-l"],
      "border-color-y": ["border-color-bs", "border-color-be", "border-color-t", "border-color-b"],
      translate: ["translate-x", "translate-y", "translate-none"],
      "translate-none": ["translate", "translate-x", "translate-y", "translate-z"],
      "scroll-m": ["scroll-mx", "scroll-my", "scroll-ms", "scroll-me", "scroll-mbs", "scroll-mbe", "scroll-mt", "scroll-mr", "scroll-mb", "scroll-ml"],
      "scroll-mx": ["scroll-ms", "scroll-me", "scroll-mr", "scroll-ml"],
      "scroll-my": ["scroll-mbs", "scroll-mbe", "scroll-mt", "scroll-mb"],
      "scroll-p": ["scroll-px", "scroll-py", "scroll-ps", "scroll-pe", "scroll-pbs", "scroll-pbe", "scroll-pt", "scroll-pr", "scroll-pb", "scroll-pl"],
      "scroll-px": ["scroll-ps", "scroll-pe", "scroll-pr", "scroll-pl"],
      "scroll-py": ["scroll-pbs", "scroll-pbe", "scroll-pt", "scroll-pb"],
      touch: ["touch-x", "touch-y", "touch-pz"],
      "touch-x": ["touch"],
      "touch-y": ["touch"],
      "touch-pz": ["touch"]
    },
    conflictingClassGroupModifiers: {
      "font-size": ["leading"]
    },
    postfixLookupClassGroups: ["container-type"],
    orderSensitiveModifiers: ["*", "**", "after", "backdrop", "before", "details-content", "file", "first-letter", "first-line", "marker", "placeholder", "selection"]
  };
}, tE = /* @__PURE__ */ D2(W2);
function Ze(...a) {
  return tE(cy(a));
}
const eE = c2(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border border-input bg-background text-foreground shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline"
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default"
    }
  }
), Go = b.forwardRef(
  ({ className: a, variant: u, size: r, asChild: c = !1, ...f }, m) => {
    const v = c ? a2 : "button";
    return /* @__PURE__ */ k.jsx(
      v,
      {
        className: Ze(eE({ variant: u, size: r, className: a })),
        ref: m,
        ...f
      }
    );
  }
);
Go.displayName = "Button";
var T0 = 1, nE = 0.9, lE = 0.8, aE = 0.17, jf = 0.1, Bf = 0.999, iE = 0.9999, oE = 0.99, uE = /[\\\/_+.#"@\[\(\{&]/, rE = /[\\\/_+.#"@\[\(\{&]/g, cE = /[\s-]/, wy = /[\s-]/g;
function If(a, u, r, c, f, m, v) {
  if (m === u.length) return f === a.length ? T0 : oE;
  var g = `${f},${m}`;
  if (v[g] !== void 0) return v[g];
  for (var p = c.charAt(m), y = r.indexOf(p, f), S = 0, d, x, C, R; y >= 0; ) d = If(a, u, r, c, y + 1, m + 1, v), d > S && (y === f ? d *= T0 : uE.test(a.charAt(y - 1)) ? (d *= lE, C = a.slice(f, y - 1).match(rE), C && f > 0 && (d *= Math.pow(Bf, C.length))) : cE.test(a.charAt(y - 1)) ? (d *= nE, R = a.slice(f, y - 1).match(wy), R && f > 0 && (d *= Math.pow(Bf, R.length))) : (d *= aE, f > 0 && (d *= Math.pow(Bf, y - f))), a.charAt(y) !== u.charAt(m) && (d *= iE)), (d < jf && r.charAt(y - 1) === c.charAt(m + 1) || c.charAt(m + 1) === c.charAt(m) && r.charAt(y - 1) !== c.charAt(m)) && (x = If(a, u, r, c, y + 1, m + 2, v), x * jf > d && (d = x * jf)), d > S && (S = d), y = r.indexOf(p, y + 1);
  return v[g] = S, S;
}
function w0(a) {
  return a.toLowerCase().replace(wy, " ");
}
function sE(a, u, r) {
  return a = r && r.length > 0 ? `${a + " " + r.join(" ")}` : a, If(a, u, w0(a), w0(u), 0, 0, {});
}
var fE = Object.defineProperty, Hi = (a, u) => fE(a, "name", { value: u, configurable: !0 }), Cy = !!(typeof window < "u" && window.document && window.document.createElement);
function ke(a, u, { checkForDefaultPrevented: r = !0 } = {}) {
  return /* @__PURE__ */ Hi(function(f) {
    if (a == null || a(f), r === !1 || !f || !f.defaultPrevented)
      return u == null ? void 0 : u(f);
  }, "handleEvent");
}
Hi(ke, "composeEventHandlers");
function dE(a) {
  var u;
  if (!Cy)
    throw new Error("Cannot access window outside of the DOM");
  return ((u = a == null ? void 0 : a.ownerDocument) == null ? void 0 : u.defaultView) ?? window;
}
Hi(dE, "getOwnerWindow");
function Pf(a) {
  if (!Cy)
    throw new Error("Cannot access document outside of the DOM");
  return (a == null ? void 0 : a.ownerDocument) ?? document;
}
Hi(Pf, "getOwnerDocument");
function Oy(a, u = !1) {
  const { activeElement: r } = Pf(a);
  if (!(r != null && r.nodeName))
    return null;
  if (_y(r) && r.contentDocument)
    return Oy(r.contentDocument.body, u);
  if (u) {
    const c = r.getAttribute("aria-activedescendant");
    if (c) {
      const f = Pf(r).getElementById(c);
      if (f)
        return f;
    }
  }
  return r;
}
Hi(Oy, "getActiveElement");
function _y(a) {
  return a.tagName === "IFRAME";
}
Hi(_y, "isFrame");
var mE = Object.defineProperty, yn = (a, u) => mE(a, "name", { value: u, configurable: !0 });
// @__NO_SIDE_EFFECTS__
function vE(a, u) {
  const r = b.createContext(u);
  r.displayName = a + "Context";
  const c = /* @__PURE__ */ yn((m) => {
    const { children: v, ...g } = m, p = b.useMemo(() => g, Object.values(g));
    return /* @__PURE__ */ k.jsx(r.Provider, { value: p, children: v });
  }, "Provider");
  c.displayName = a + "Provider";
  function f(m, v = {}) {
    const { optional: g = !1 } = v, p = b.useContext(r);
    if (p) return p;
    if (u !== void 0) return u;
    if (!g)
      throw new Error(`\`${m}\` must be used within \`${a}\``);
  }
  return yn(f, "useContext"), [c, f];
}
yn(vE, "createContext");
// @__NO_SIDE_EFFECTS__
function Qr(a, u = []) {
  let r = [];
  function c(m, v) {
    const g = b.createContext(v);
    g.displayName = m + "Context";
    const p = r.length;
    r = [...r, v];
    const y = /* @__PURE__ */ yn((d) => {
      var H;
      const { scope: x, children: C, ...R } = d, O = ((H = x == null ? void 0 : x[a]) == null ? void 0 : H[p]) || g, N = b.useMemo(() => R, Object.values(R));
      return /* @__PURE__ */ k.jsx(O.Provider, { value: N, children: C });
    }, "Provider");
    y.displayName = m + "Provider";
    function S(d, x, C = {}) {
      var H;
      const { optional: R = !1 } = C, O = ((H = x == null ? void 0 : x[a]) == null ? void 0 : H[p]) || g, N = b.useContext(O);
      if (N) return N;
      if (v !== void 0) return v;
      if (!R)
        throw new Error(`\`${d}\` must be used within \`${m}\``);
    }
    return yn(S, "useContext"), [y, S];
  }
  yn(c, "createContext");
  const f = /* @__PURE__ */ yn(() => {
    const m = r.map((v) => b.createContext(v));
    return /* @__PURE__ */ yn(function(g) {
      const p = (g == null ? void 0 : g[a]) || m;
      return b.useMemo(
        () => ({ [`__scope${a}`]: { ...g, [a]: p } }),
        [g, p]
      );
    }, "useScope");
  }, "createScope");
  return f.scopeName = a, [c, Ay(f, ...u)];
}
yn(Qr, "createContextScope");
function Ay(...a) {
  const u = a[0];
  if (a.length === 1) return u;
  const r = /* @__PURE__ */ yn(() => {
    const c = a.map((f) => ({
      useScope: f(),
      scopeName: f.scopeName
    }));
    return /* @__PURE__ */ yn(function(m) {
      const v = c.reduce((g, { useScope: p, scopeName: y }) => {
        const d = p(m)[`__scope${y}`];
        return { ...g, ...d };
      }, {});
      return b.useMemo(() => ({ [`__scope${u.scopeName}`]: v }), [v]);
    }, "useComposedScopes");
  }, "createScope");
  return r.scopeName = u.scopeName, r;
}
yn(Ay, "composeContextScopes");
var ln = globalThis != null && globalThis.document ? b.useLayoutEffect : () => {
}, hE = Object.defineProperty, gE = (a, u) => hE(a, "name", { value: u, configurable: !0 }), yE = Ko[" useId ".trim().toString()] || (() => {
}), pE = 0;
function An(a) {
  const [u, r] = b.useState(yE());
  return ln(() => {
    a || r((c) => c ?? String(pE++));
  }, [a]), a || (u ? `radix-${u}` : "");
}
gE(An, "useId");
var bE = Object.defineProperty, SE = (a, u) => bE(a, "name", { value: u, configurable: !0 }), C0 = Ko[" useEffectEvent ".trim().toString()], O0 = Ko[" useInsertionEffect ".trim().toString()];
function Ry(a) {
  if (typeof C0 == "function")
    return C0(a);
  const u = b.useRef(() => {
    throw new Error("Cannot call an event handler while rendering.");
  });
  return typeof O0 == "function" ? O0(() => {
    u.current = a;
  }) : ln(() => {
    u.current = a;
  }), b.useMemo(() => ((...r) => {
    var c;
    return (c = u.current) == null ? void 0 : c.call(u, ...r);
  }), []);
}
SE(Ry, "useEffectEvent");
var EE = Object.defineProperty, Jo = (a, u) => EE(a, "name", { value: u, configurable: !0 }), xE = Ko[" useInsertionEffect ".trim().toString()] || ln;
function yd({
  prop: a,
  defaultProp: u,
  onChange: r = /* @__PURE__ */ Jo(() => {
  }, "onChange"),
  caller: c
}) {
  const [f, m, v] = Ny({
    defaultProp: u,
    onChange: r
  }), g = a !== void 0, p = g ? a : f, y = b.useCallback(
    (S) => {
      var d;
      if (g) {
        const x = Dy(S) ? S(a) : S;
        x !== a && ((d = v.current) == null || d.call(v, x));
      } else
        m(S);
    },
    [g, a, m, v]
  );
  return [p, y];
}
Jo(yd, "useControllableState");
function Ny({
  defaultProp: a,
  onChange: u
}) {
  const [r, c] = b.useState(a), f = b.useRef(r), m = b.useRef(u);
  return xE(() => {
    m.current = u;
  }, [u]), b.useEffect(() => {
    var v;
    f.current !== r && ((v = m.current) == null || v.call(m, r), f.current = r);
  }, [r, f]), [r, c, m];
}
Jo(Ny, "useUncontrolledState");
function Dy(a) {
  return typeof a == "function";
}
Jo(Dy, "isFunction");
var _0 = Symbol("RADIX:SYNC_STATE");
function TE(a, u, r, c) {
  const { prop: f, defaultProp: m, onChange: v, caller: g } = u, p = f !== void 0, y = Ry(v), S = [{ ...r, state: m }];
  c && S.push(c);
  const [d, x] = b.useReducer(
    (N, H) => {
      if (H.type === _0)
        return { ...N, state: H.state };
      const L = a(N, H);
      return p && !Object.is(L.state, N.state) && y(L.state), L;
    },
    ...S
  ), C = d.state, R = b.useRef(C);
  b.useEffect(() => {
    R.current !== C && (R.current = C, p || y(C));
  }, [C, R, p]);
  const O = b.useMemo(() => f !== void 0 ? { ...d, state: f } : d, [d, f]);
  return b.useEffect(() => {
    p && !Object.is(f, d.state) && x({ type: _0, state: f });
  }, [f, d.state, p]), [O, x];
}
Jo(TE, "useControllableStateReducer");
var Zr = ey();
const wE = /* @__PURE__ */ ty(Zr);
var CE = Object.defineProperty, OE = (a, u) => CE(a, "name", { value: u, configurable: !0 }), _E = [
  "a",
  "button",
  "div",
  "form",
  "h2",
  "h3",
  "img",
  "input",
  "label",
  "li",
  "nav",
  "ol",
  "p",
  "select",
  "span",
  "svg",
  "ul"
], se = _E.reduce((a, u) => {
  const r = /* @__PURE__ */ kr(`Primitive.${u}`), c = b.forwardRef((f, m) => {
    const { asChild: v, ...g } = f, p = v ? r : u;
    return typeof window < "u" && (window[Symbol.for("radix-ui")] = !0), /* @__PURE__ */ k.jsx(p, { ...g, ref: m });
  });
  return c.displayName = `Primitive.${u}`, { ...a, [u]: c };
}, {});
function zy(a, u) {
  a && Zr.flushSync(() => a.dispatchEvent(u));
}
OE(zy, "dispatchDiscreteCustomEvent");
var AE = Object.defineProperty, RE = (a, u) => AE(a, "name", { value: u, configurable: !0 });
function Na(a) {
  const u = b.useRef(a);
  return b.useEffect(() => {
    u.current = a;
  }), b.useMemo(() => ((...r) => {
    var c;
    return (c = u.current) == null ? void 0 : c.call(u, ...r);
  }), []);
}
RE(Na, "useCallbackRef");
var NE = Object.defineProperty, he = (a, u) => NE(a, "name", { value: u, configurable: !0 }), Wf = "dismissableLayer.update", DE = "dismissableLayer.pointerDownOutside", zE = "dismissableLayer.focusOutside", A0, My = b.createContext({
  layers: /* @__PURE__ */ new Set(),
  layersWithOutsidePointerEventsDisabled: /* @__PURE__ */ new Set(),
  branches: /* @__PURE__ */ new Set(),
  // Outside elements that belong to a layer's own dismiss affordance (eg, a
  // dialog overlay). Pressing them should dismiss the layer regardless of
  // whether or not they stop propagation.
  //
  // See https://github.com/radix-ui/primitives/issues/3346
  dismissableSurfaces: /* @__PURE__ */ new Set()
}), Uy = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ he(function(u, r) {
    const {
      disableOutsidePointerEvents: c = !1,
      deferPointerDownOutside: f = !1,
      onEscapeKeyDown: m,
      onPointerDownOutside: v,
      onFocusOutside: g,
      onInteractOutside: p,
      onDismiss: y,
      ...S
    } = u, d = b.useContext(My), [x, C] = b.useState(null), R = (x == null ? void 0 : x.ownerDocument) ?? (globalThis == null ? void 0 : globalThis.document), [, O] = b.useState({}), N = Fn(r, C), H = Array.from(d.layers), [L] = [
      ...d.layersWithOutsidePointerEventsDisabled
    ].slice(-1), J = L ? H.indexOf(L) : -1, K = x ? H.indexOf(x) : -1, I = d.layersWithOutsidePointerEventsDisabled.size > 0, Z = K >= J, X = b.useRef(!1), Y = jy(
      (st) => {
        v == null || v(st), p == null || p(st), st.defaultPrevented || y == null || y();
      },
      {
        ownerDocument: R,
        deferPointerDownOutside: f,
        isDeferredPointerDownOutsideRef: X,
        dismissableSurfaces: d.dismissableSurfaces,
        shouldHandlePointerDownOutside: b.useCallback(
          (st) => {
            if (!(st instanceof Node))
              return !1;
            const Tt = [...d.branches].some(
              (gt) => gt.contains(st)
            );
            return Z && !Tt;
          },
          [d.branches, Z]
        )
      }
    ), dt = By((st) => {
      if (f && X.current)
        return;
      const Tt = st.target;
      [...d.branches].some((yt) => yt.contains(Tt)) || (g == null || g(st), p == null || p(st), st.defaultPrevented || y == null || y());
    }, R), ht = x ? K === H.length - 1 : !1, xt = Na((st) => {
      st.key === "Escape" && (m == null || m(st), !st.defaultPrevented && y && (st.preventDefault(), y()));
    });
    return b.useEffect(() => {
      if (ht)
        return R.addEventListener("keydown", xt, { capture: !0 }), () => R.removeEventListener("keydown", xt, { capture: !0 });
    }, [R, ht, xt]), b.useEffect(() => {
      if (x)
        return c && (d.layersWithOutsidePointerEventsDisabled.size === 0 && (A0 = R.body.style.pointerEvents, R.body.style.pointerEvents = "none"), d.layersWithOutsidePointerEventsDisabled.add(x)), d.layers.add(x), td(), () => {
          c && (d.layersWithOutsidePointerEventsDisabled.delete(x), d.layersWithOutsidePointerEventsDisabled.size === 0 && (R.body.style.pointerEvents = A0));
        };
    }, [x, R, c, d]), b.useEffect(() => () => {
      x && (d.layers.delete(x), d.layersWithOutsidePointerEventsDisabled.delete(x), td());
    }, [x, d]), b.useEffect(() => {
      const st = /* @__PURE__ */ he(() => O({}), "handleUpdate");
      return document.addEventListener(Wf, st), () => document.removeEventListener(Wf, st);
    }, []), /* @__PURE__ */ k.jsx(
      se.div,
      {
        ...S,
        ref: N,
        style: {
          pointerEvents: I ? Z ? "auto" : "none" : void 0,
          ...u.style
        },
        onFocusCapture: ke(u.onFocusCapture, dt.onFocusCapture),
        onBlurCapture: ke(u.onBlurCapture, dt.onBlurCapture),
        onPointerDownCapture: ke(
          u.onPointerDownCapture,
          Y.onPointerDownCapture
        )
      }
    );
  }, "DismissableLayer")
);
function Hy() {
  const a = b.useContext(My), [u, r] = b.useState(null);
  return b.useEffect(() => {
    if (u)
      return a.dismissableSurfaces.add(u), () => {
        a.dismissableSurfaces.delete(u);
      };
  }, [u, a.dismissableSurfaces]), r;
}
he(Hy, "useDismissableLayerSurface");
var ME = /* @__PURE__ */ he(() => !0, "IS_TRUE");
function jy(a, u) {
  const {
    ownerDocument: r = globalThis == null ? void 0 : globalThis.document,
    deferPointerDownOutside: c = !1,
    isDeferredPointerDownOutsideRef: f,
    dismissableSurfaces: m,
    shouldHandlePointerDownOutside: v = ME
  } = u, g = Na(a), p = b.useRef(!1), y = b.useRef(!1), S = b.useRef(/* @__PURE__ */ new Map()), d = b.useRef(() => {
  });
  return b.useEffect(() => {
    function x() {
      y.current = !1, f.current = !1, S.current.clear();
    }
    he(x, "resetOutsideInteraction");
    function C() {
      return Array.from(S.current.values()).some(Boolean);
    }
    he(C, "isOutsideInteractionIntercepted");
    function R(J) {
      if (!y.current)
        return;
      const K = J.target;
      K instanceof Node && [...m].some((Z) => Z.contains(K)) || S.current.set(J.type, !0), J.type === "click" && window.setTimeout(() => {
        y.current && d.current();
      }, 0);
    }
    he(R, "handleInteractionCapture");
    function O(J) {
      y.current && S.current.set(J.type, !1);
    }
    he(O, "handleInteractionBubble");
    const N = /* @__PURE__ */ he((J) => {
      if (J.target && !p.current) {
        let K = function() {
          r.removeEventListener("click", d.current);
          const Z = C();
          x(), Z || pd(
            DE,
            g,
            I,
            { discrete: !0 }
          );
        };
        if (he(K, "handleAndDispatchPointerDownOutsideEvent"), !v(J.target)) {
          r.removeEventListener("click", d.current), x(), p.current = !1;
          return;
        }
        const I = { originalEvent: J };
        y.current = !0, f.current = c && J.button === 0, S.current.clear(), !c || J.button !== 0 ? K() : (r.removeEventListener("click", d.current), d.current = K, r.addEventListener("click", d.current, { once: !0 }));
      } else
        r.removeEventListener("click", d.current), x();
      p.current = !1;
    }, "handlePointerDown"), H = [
      "pointerup",
      "mousedown",
      "mouseup",
      "touchstart",
      "touchend",
      "click"
    ];
    for (const J of H)
      r.addEventListener(J, R, !0), r.addEventListener(J, O);
    const L = window.setTimeout(() => {
      r.addEventListener("pointerdown", N);
    }, 0);
    return () => {
      window.clearTimeout(L), r.removeEventListener("pointerdown", N), r.removeEventListener("click", d.current);
      for (const J of H)
        r.removeEventListener(J, R, !0), r.removeEventListener(J, O);
    };
  }, [
    r,
    g,
    c,
    f,
    m,
    v
  ]), {
    // ensures we check React component tree (not just DOM tree)
    onPointerDownCapture: /* @__PURE__ */ he(() => p.current = !0, "onPointerDownCapture")
  };
}
he(jy, "usePointerDownOutside");
function By(a, u = globalThis == null ? void 0 : globalThis.document) {
  const r = Na(a), c = b.useRef(!1);
  return b.useEffect(() => {
    const f = /* @__PURE__ */ he((m) => {
      m.target && !c.current && pd(zE, r, { originalEvent: m }, {
        discrete: !1
      });
    }, "handleFocus");
    return u.addEventListener("focusin", f), () => u.removeEventListener("focusin", f);
  }, [u, r]), {
    onFocusCapture: /* @__PURE__ */ he(() => c.current = !0, "onFocusCapture"),
    onBlurCapture: /* @__PURE__ */ he(() => c.current = !1, "onBlurCapture")
  };
}
he(By, "useFocusOutside");
function td() {
  const a = new CustomEvent(Wf);
  document.dispatchEvent(a);
}
he(td, "dispatchUpdate");
function pd(a, u, r, { discrete: c }) {
  const f = r.originalEvent.target, m = new CustomEvent(a, { bubbles: !1, cancelable: !0, detail: r });
  u && f.addEventListener(a, u, { once: !0 }), c ? zy(f, m) : f.dispatchEvent(m);
}
he(pd, "handleAndDispatchCustomEvent");
var UE = Object.defineProperty, Ue = (a, u) => UE(a, "name", { value: u, configurable: !0 }), Lf = "focusScope.autoFocusOnMount", Yf = "focusScope.autoFocusOnUnmount", R0 = { bubbles: !1, cancelable: !0 }, HE = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ Ue(function(u, r) {
    const {
      loop: c = !1,
      trapped: f = !1,
      onMountAutoFocus: m,
      onUnmountAutoFocus: v,
      ...g
    } = u, [p, y] = b.useState(null), S = Na(m), d = Na(v), x = b.useRef(null), C = Fn(r, y), R = b.useRef({
      paused: !1,
      pause() {
        this.paused = !0;
      },
      resume() {
        this.paused = !1;
      }
    }).current;
    b.useEffect(() => {
      if (f) {
        let N = function(K) {
          if (R.paused || !p) return;
          const I = K.target;
          p.contains(I) ? x.current = I : hl(x.current, { select: !0 });
        }, H = function(K) {
          if (R.paused || !p) return;
          const I = K.relatedTarget;
          I !== null && (p.contains(I) || hl(x.current, { select: !0 }));
        }, L = function(K) {
          if (document.activeElement === document.body)
            for (const Z of K)
              Z.removedNodes.length > 0 && hl(p);
        };
        Ue(N, "handleFocusIn"), Ue(H, "handleFocusOut"), Ue(L, "handleMutations"), document.addEventListener("focusin", N), document.addEventListener("focusout", H);
        const J = new MutationObserver(L);
        return p && J.observe(p, { childList: !0, subtree: !0 }), () => {
          document.removeEventListener("focusin", N), document.removeEventListener("focusout", H), J.disconnect();
        };
      }
    }, [f, p, R.paused]), b.useEffect(() => {
      if (p) {
        N0.add(R);
        const N = document.activeElement;
        if (!p.contains(N)) {
          const L = new CustomEvent(Lf, R0);
          p.addEventListener(Lf, S), p.dispatchEvent(L), L.defaultPrevented || (Ly(Xy(bd(p)), { select: !0 }), document.activeElement === N && hl(p));
        }
        return () => {
          p.removeEventListener(Lf, S), setTimeout(() => {
            const L = new CustomEvent(Yf, R0);
            p.addEventListener(Yf, d), p.dispatchEvent(L), L.defaultPrevented || hl(N ?? document.body, { select: !0 }), p.removeEventListener(Yf, d), N0.remove(R);
          }, 0);
        };
      }
    }, [p, S, d, R]);
    const O = b.useCallback(
      (N) => {
        if (!c && !f || R.paused) return;
        const H = N.key === "Tab" && !N.altKey && !N.ctrlKey && !N.metaKey, L = document.activeElement;
        if (H && L) {
          const J = N.currentTarget, [K, I] = Yy(J);
          K && I ? !N.shiftKey && L === I ? (N.preventDefault(), c && hl(K, { select: !0 })) : N.shiftKey && L === K && (N.preventDefault(), c && hl(I, { select: !0 })) : L === J && N.preventDefault();
        }
      },
      [c, f, R.paused]
    );
    return /* @__PURE__ */ k.jsx(se.div, { tabIndex: -1, ...g, ref: C, onKeyDown: O });
  }, "FocusScope")
);
function Ly(a, { select: u = !1 } = {}) {
  const r = document.activeElement;
  for (const c of a)
    if (hl(c, { select: u }), document.activeElement !== r) return;
}
Ue(Ly, "focusFirst");
function Yy(a) {
  const u = bd(a), r = ed(u, a), c = ed(u.reverse(), a);
  return [r, c];
}
Ue(Yy, "getTabbableEdges");
function bd(a) {
  const u = [], r = document.createTreeWalker(a, NodeFilter.SHOW_ELEMENT, {
    acceptNode: /* @__PURE__ */ Ue((c) => {
      const f = c.tagName === "INPUT" && c.type === "hidden";
      return c.disabled || c.hidden || f ? NodeFilter.FILTER_SKIP : c.tabIndex >= 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
    }, "acceptNode")
  });
  for (; r.nextNode(); ) u.push(r.currentNode);
  return u;
}
Ue(bd, "getTabbableCandidates");
function ed(a, u) {
  const r = typeof u.checkVisibility == "function" && u.checkVisibility({ checkVisibilityCSS: !0 });
  for (const c of a)
    if (!(r ? !c.checkVisibility({ checkVisibilityCSS: !0 }) : qy(c, { upTo: u })))
      return c;
}
Ue(ed, "findVisible");
function qy(a, { upTo: u }) {
  if (getComputedStyle(a).visibility === "hidden") return !0;
  for (; a; ) {
    if (u !== void 0 && a === u) return !1;
    if (getComputedStyle(a).display === "none") return !0;
    a = a.parentElement;
  }
  return !1;
}
Ue(qy, "isHidden");
function Vy(a) {
  return a instanceof HTMLInputElement && "select" in a;
}
Ue(Vy, "isSelectableInput");
function hl(a, { select: u = !1 } = {}) {
  if (a && a.focus) {
    const r = document.activeElement;
    a.focus({ preventScroll: !0 }), a !== r && Vy(a) && u && a.select();
  }
}
Ue(hl, "focus");
var N0 = Gy();
function Gy() {
  let a = [];
  return {
    add(u) {
      const r = a[0];
      u !== r && (r == null || r.pause()), a = nd(a, u), a.unshift(u);
    },
    remove(u) {
      var r;
      a = nd(a, u), (r = a[0]) == null || r.resume();
    }
  };
}
Ue(Gy, "createFocusScopesStack");
function nd(a, u) {
  const r = [...a], c = r.indexOf(u);
  return c !== -1 && r.splice(c, 1), r;
}
Ue(nd, "arrayRemove");
function Xy(a) {
  return a.filter((u) => u.tagName !== "A");
}
Ue(Xy, "removeLinks");
var jE = Object.defineProperty, BE = (a, u) => jE(a, "name", { value: u, configurable: !0 }), ky = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ BE(function(u, r) {
    var p;
    const { container: c, ...f } = u, [m, v] = b.useState(!1);
    ln(() => v(!0), []);
    const g = c || m && ((p = globalThis == null ? void 0 : globalThis.document) == null ? void 0 : p.body);
    return g ? Zr.createPortal(/* @__PURE__ */ k.jsx(se.div, { ...f, ref: r }), g) : null;
  }, "Portal")
), LE = Object.defineProperty, pl = (a, u) => LE(a, "name", { value: u, configurable: !0 });
function Qy(a, u) {
  return b.useReducer((r, c) => u[r][c] ?? r, a);
}
pl(Qy, "useStateMachine");
var Fo = /* @__PURE__ */ pl((a) => {
  const { present: u, children: r } = a, c = Zy(u), f = typeof r == "function" ? r({ present: c.isPresent }) : b.Children.only(r), m = Ky(c.ref, Jy(f));
  return typeof r == "function" || c.isPresent ? b.cloneElement(f, { ref: m }) : null;
}, "Presence");
function Zy(a) {
  const [u, r] = b.useState(), c = b.useRef(null), f = b.useRef(a), m = b.useRef("none"), v = b.useRef(void 0), g = a ? "mounted" : "unmounted", [p, y] = Qy(g, {
    mounted: {
      UNMOUNT: "unmounted",
      ANIMATION_OUT: "unmountSuspended"
    },
    unmountSuspended: {
      MOUNT: "mounted",
      ANIMATION_END: "unmounted"
    },
    unmounted: {
      MOUNT: "mounted"
    }
  });
  return b.useEffect(() => {
    p === "mounted" ? (m.current = v.current ?? Ni(c.current), v.current = void 0) : m.current = "none";
  }, [p]), ln(() => {
    const S = c.current, d = f.current;
    if (d !== a) {
      const C = m.current, R = Ni(S);
      a ? (v.current = R, y("MOUNT")) : R === "none" || (S == null ? void 0 : S.display) === "none" ? y("UNMOUNT") : y(d && C !== R ? "ANIMATION_OUT" : "UNMOUNT"), f.current = a;
    }
  }, [a, y]), ln(() => {
    if (u) {
      let S;
      const d = u.ownerDocument.defaultView ?? window, x = /* @__PURE__ */ pl((R) => {
        const N = Ni(c.current).includes(CSS.escape(R.animationName));
        if (R.target === u && N && (y("ANIMATION_END"), !f.current)) {
          const H = u.style.animationFillMode;
          u.style.animationFillMode = "forwards", S = d.setTimeout(() => {
            u.style.animationFillMode === "forwards" && (u.style.animationFillMode = H);
          });
        }
      }, "handleAnimationEnd"), C = /* @__PURE__ */ pl((R) => {
        R.target === u && (m.current = Ni(c.current));
      }, "handleAnimationStart");
      return u.addEventListener("animationstart", C), u.addEventListener("animationcancel", x), u.addEventListener("animationend", x), () => {
        d.clearTimeout(S), u.removeEventListener("animationstart", C), u.removeEventListener("animationcancel", x), u.removeEventListener("animationend", x);
      };
    } else
      y("ANIMATION_END");
  }, [u, y]), {
    isPresent: ["mounted", "unmountSuspended"].includes(p),
    ref: b.useCallback((S) => {
      if (S) {
        const d = getComputedStyle(S);
        c.current = d, v.current = Ni(d);
      } else
        c.current = null;
      r(S);
    }, [])
  };
}
pl(Zy, "usePresence");
function ld(a, u) {
  if (typeof a == "function")
    return a(u);
  a != null && (a.current = u);
}
pl(ld, "setRef");
function Ky(...a) {
  const u = b.useRef(a);
  return u.current = a, b.useCallback((r) => {
    const c = u.current;
    let f = !1;
    const m = c.map((v) => {
      const g = ld(v, r);
      return !f && typeof g == "function" && (f = !0), g;
    });
    if (f)
      return () => {
        for (let v = 0; v < m.length; v++) {
          const g = m[v];
          typeof g == "function" ? g() : ld(c[v], null);
        }
      };
  }, []);
}
pl(Ky, "useStableComposedRefs");
function Ni(a) {
  return (a == null ? void 0 : a.animationName) || "none";
}
pl(Ni, "getAnimationName");
function Jy(a) {
  var c, f;
  let u = (c = Object.getOwnPropertyDescriptor(a.props, "ref")) == null ? void 0 : c.get, r = u && "isReactWarning" in u && u.isReactWarning;
  return r ? a.ref : (u = (f = Object.getOwnPropertyDescriptor(a, "ref")) == null ? void 0 : f.get, r = u && "isReactWarning" in u && u.isReactWarning, r ? a.props.ref : a.props.ref || a.ref);
}
pl(Jy, "getElementRef");
var YE = Object.defineProperty, Sd = (a, u) => YE(a, "name", { value: u, configurable: !0 }), Rr = 0, Xn = null;
function qE(a) {
  return Ed(), a.children;
}
Sd(qE, "FocusGuards");
function Ed() {
  b.useEffect(() => {
    Xn || (Xn = { start: ad(), end: ad() });
    const { start: a, end: u } = Xn;
    return document.body.firstElementChild !== a && document.body.insertAdjacentElement("afterbegin", a), document.body.lastElementChild !== u && document.body.insertAdjacentElement("beforeend", u), Rr++, () => {
      Rr === 1 && (Xn == null || Xn.start.remove(), Xn == null || Xn.end.remove(), Xn = null), Rr = Math.max(0, Rr - 1);
    };
  }, []);
}
Sd(Ed, "useFocusGuards");
function ad() {
  const a = document.createElement("span");
  return a.setAttribute("data-radix-focus-guard", ""), a.tabIndex = 0, a.style.outline = "none", a.style.opacity = "0", a.style.position = "fixed", a.style.pointerEvents = "none", a;
}
Sd(ad, "createFocusGuard");
var Qn = function() {
  return Qn = Object.assign || function(u) {
    for (var r, c = 1, f = arguments.length; c < f; c++) {
      r = arguments[c];
      for (var m in r) Object.prototype.hasOwnProperty.call(r, m) && (u[m] = r[m]);
    }
    return u;
  }, Qn.apply(this, arguments);
};
function Fy(a, u) {
  var r = {};
  for (var c in a) Object.prototype.hasOwnProperty.call(a, c) && u.indexOf(c) < 0 && (r[c] = a[c]);
  if (a != null && typeof Object.getOwnPropertySymbols == "function")
    for (var f = 0, c = Object.getOwnPropertySymbols(a); f < c.length; f++)
      u.indexOf(c[f]) < 0 && Object.prototype.propertyIsEnumerable.call(a, c[f]) && (r[c[f]] = a[c[f]]);
  return r;
}
function VE(a, u, r) {
  if (r || arguments.length === 2) for (var c = 0, f = u.length, m; c < f; c++)
    (m || !(c in u)) && (m || (m = Array.prototype.slice.call(u, 0, c)), m[c] = u[c]);
  return a.concat(m || Array.prototype.slice.call(u));
}
var jr = "right-scroll-bar-position", Br = "width-before-scroll-bar", GE = "with-scroll-bars-hidden", XE = "--removed-body-scroll-bar-size";
function qf(a, u) {
  return typeof a == "function" ? a(u) : a && (a.current = u), a;
}
function kE(a, u) {
  var r = b.useState(function() {
    return {
      // value
      value: a,
      // last callback
      callback: u,
      // "memoized" public interface
      facade: {
        get current() {
          return r.value;
        },
        set current(c) {
          var f = r.value;
          f !== c && (r.value = c, r.callback(c, f));
        }
      }
    };
  })[0];
  return r.callback = u, r.facade;
}
var QE = typeof window < "u" ? b.useLayoutEffect : b.useEffect, D0 = /* @__PURE__ */ new WeakMap();
function ZE(a, u) {
  var r = kE(null, function(c) {
    return a.forEach(function(f) {
      return qf(f, c);
    });
  });
  return QE(function() {
    var c = D0.get(r);
    if (c) {
      var f = new Set(c), m = new Set(a), v = r.current;
      f.forEach(function(g) {
        m.has(g) || qf(g, null);
      }), m.forEach(function(g) {
        f.has(g) || qf(g, v);
      });
    }
    D0.set(r, a);
  }, [a]), r;
}
function KE(a) {
  return a;
}
function JE(a, u) {
  u === void 0 && (u = KE);
  var r = [], c = !1, f = {
    read: function() {
      if (c)
        throw new Error("Sidecar: could not `read` from an `assigned` medium. `read` could be used only with `useMedium`.");
      return r.length ? r[r.length - 1] : a;
    },
    useMedium: function(m) {
      var v = u(m, c);
      return r.push(v), function() {
        r = r.filter(function(g) {
          return g !== v;
        });
      };
    },
    assignSyncMedium: function(m) {
      for (c = !0; r.length; ) {
        var v = r;
        r = [], v.forEach(m);
      }
      r = {
        push: function(g) {
          return m(g);
        },
        filter: function() {
          return r;
        }
      };
    },
    assignMedium: function(m) {
      c = !0;
      var v = [];
      if (r.length) {
        var g = r;
        r = [], g.forEach(m), v = r;
      }
      var p = function() {
        var S = v;
        v = [], S.forEach(m);
      }, y = function() {
        return Promise.resolve().then(p);
      };
      y(), r = {
        push: function(S) {
          v.push(S), y();
        },
        filter: function(S) {
          return v = v.filter(S), r;
        }
      };
    }
  };
  return f;
}
function FE(a) {
  a === void 0 && (a = {});
  var u = JE(null);
  return u.options = Qn({ async: !0, ssr: !1 }, a), u;
}
var $y = function(a) {
  var u = a.sideCar, r = Fy(a, ["sideCar"]);
  if (!u)
    throw new Error("Sidecar: please provide `sideCar` property to import the right car");
  var c = u.read();
  if (!c)
    throw new Error("Sidecar medium not found");
  return b.createElement(c, Qn({}, r));
};
$y.isSideCarExport = !0;
function $E(a, u) {
  return a.useMedium(u), $y;
}
var Iy = FE(), Vf = function() {
}, Kr = b.forwardRef(function(a, u) {
  var r = b.useRef(null), c = b.useState({
    onScrollCapture: Vf,
    onWheelCapture: Vf,
    onTouchMoveCapture: Vf
  }), f = c[0], m = c[1], v = a.forwardProps, g = a.children, p = a.className, y = a.removeScrollBar, S = a.enabled, d = a.shards, x = a.sideCar, C = a.noRelative, R = a.noIsolation, O = a.inert, N = a.allowPinchZoom, H = a.as, L = H === void 0 ? "div" : H, J = a.gapMode, K = Fy(a, ["forwardProps", "children", "className", "removeScrollBar", "enabled", "shards", "sideCar", "noRelative", "noIsolation", "inert", "allowPinchZoom", "as", "gapMode"]), I = x, Z = ZE([r, u]), X = Qn(Qn({}, K), f);
  return b.createElement(
    b.Fragment,
    null,
    S && b.createElement(I, { sideCar: Iy, removeScrollBar: y, shards: d, noRelative: C, noIsolation: R, inert: O, setCallbacks: m, allowPinchZoom: !!N, lockRef: r, gapMode: J }),
    v ? b.cloneElement(b.Children.only(g), Qn(Qn({}, X), { ref: Z })) : b.createElement(L, Qn({}, X, { className: p, ref: Z }), g)
  );
});
Kr.defaultProps = {
  enabled: !0,
  removeScrollBar: !0,
  inert: !1
};
Kr.classNames = {
  fullWidth: Br,
  zeroRight: jr
};
var IE = function() {
  if (typeof __webpack_nonce__ < "u")
    return __webpack_nonce__;
};
function PE() {
  if (!document)
    return null;
  var a = document.createElement("style");
  a.type = "text/css";
  var u = IE();
  return u && a.setAttribute("nonce", u), a;
}
function WE(a, u) {
  a.styleSheet ? a.styleSheet.cssText = u : a.appendChild(document.createTextNode(u));
}
function tx(a) {
  var u = document.head || document.getElementsByTagName("head")[0];
  u.appendChild(a);
}
var ex = function() {
  var a = 0, u = null;
  return {
    add: function(r) {
      a == 0 && (u = PE()) && (WE(u, r), tx(u)), a++;
    },
    remove: function() {
      a--, !a && u && (u.parentNode && u.parentNode.removeChild(u), u = null);
    }
  };
}, nx = function() {
  var a = ex();
  return function(u, r) {
    b.useEffect(function() {
      return a.add(u), function() {
        a.remove();
      };
    }, [u && r]);
  };
}, Py = function() {
  var a = nx(), u = function(r) {
    var c = r.styles, f = r.dynamic;
    return a(c, f), null;
  };
  return u;
}, lx = {
  left: 0,
  top: 0,
  right: 0,
  gap: 0
}, Gf = function(a) {
  return parseInt(a || "", 10) || 0;
}, ax = function(a) {
  var u = window.getComputedStyle(document.body), r = u[a === "padding" ? "paddingLeft" : "marginLeft"], c = u[a === "padding" ? "paddingTop" : "marginTop"], f = u[a === "padding" ? "paddingRight" : "marginRight"];
  return [Gf(r), Gf(c), Gf(f)];
}, ix = function(a) {
  if (a === void 0 && (a = "margin"), typeof window > "u")
    return lx;
  var u = ax(a), r = document.documentElement.clientWidth, c = window.innerWidth;
  return {
    left: u[0],
    top: u[1],
    right: u[2],
    gap: Math.max(0, c - r + u[2] - u[0])
  };
}, ox = Py(), Mi = "data-scroll-locked", ux = function(a, u, r, c) {
  var f = a.left, m = a.top, v = a.right, g = a.gap;
  return r === void 0 && (r = "margin"), `
  .`.concat(GE, ` {
   overflow: hidden `).concat(c, `;
   padding-right: `).concat(g, "px ").concat(c, `;
  }
  body[`).concat(Mi, `] {
    overflow: hidden `).concat(c, `;
    overscroll-behavior: contain;
    `).concat([
    u && "position: relative ".concat(c, ";"),
    r === "margin" && `
    padding-left: `.concat(f, `px;
    padding-top: `).concat(m, `px;
    padding-right: `).concat(v, `px;
    margin-left:0;
    margin-top:0;
    margin-right: `).concat(g, "px ").concat(c, `;
    `),
    r === "padding" && "padding-right: ".concat(g, "px ").concat(c, ";")
  ].filter(Boolean).join(""), `
  }
  
  .`).concat(jr, ` {
    right: `).concat(g, "px ").concat(c, `;
  }
  
  .`).concat(Br, ` {
    margin-right: `).concat(g, "px ").concat(c, `;
  }
  
  .`).concat(jr, " .").concat(jr, ` {
    right: 0 `).concat(c, `;
  }
  
  .`).concat(Br, " .").concat(Br, ` {
    margin-right: 0 `).concat(c, `;
  }
  
  body[`).concat(Mi, `] {
    `).concat(XE, ": ").concat(g, `px;
  }
`);
}, z0 = function() {
  var a = parseInt(document.body.getAttribute(Mi) || "0", 10);
  return isFinite(a) ? a : 0;
}, rx = function() {
  b.useEffect(function() {
    return document.body.setAttribute(Mi, (z0() + 1).toString()), function() {
      var a = z0() - 1;
      a <= 0 ? document.body.removeAttribute(Mi) : document.body.setAttribute(Mi, a.toString());
    };
  }, []);
}, cx = function(a) {
  var u = a.noRelative, r = a.noImportant, c = a.gapMode, f = c === void 0 ? "margin" : c;
  rx();
  var m = b.useMemo(function() {
    return ix(f);
  }, [f]);
  return b.createElement(ox, { styles: ux(m, !u, f, r ? "" : "!important") });
}, id = !1;
if (typeof window < "u")
  try {
    var Nr = Object.defineProperty({}, "passive", {
      get: function() {
        return id = !0, !0;
      }
    });
    window.addEventListener("test", Nr, Nr), window.removeEventListener("test", Nr, Nr);
  } catch {
    id = !1;
  }
var _i = id ? { passive: !1 } : !1, sx = function(a) {
  return a.tagName === "TEXTAREA";
}, Wy = function(a, u) {
  if (!(a instanceof Element))
    return !1;
  var r = window.getComputedStyle(a);
  return (
    // not-not-scrollable
    r[u] !== "hidden" && // contains scroll inside self
    !(r.overflowY === r.overflowX && !sx(a) && r[u] === "visible")
  );
}, fx = function(a) {
  return Wy(a, "overflowY");
}, dx = function(a) {
  return Wy(a, "overflowX");
}, M0 = function(a, u) {
  var r = u.ownerDocument, c = u;
  do {
    typeof ShadowRoot < "u" && c instanceof ShadowRoot && (c = c.host);
    var f = tp(a, c);
    if (f) {
      var m = ep(a, c), v = m[1], g = m[2];
      if (v > g)
        return !0;
    }
    c = c.parentNode;
  } while (c && c !== r.body);
  return !1;
}, mx = function(a) {
  var u = a.scrollTop, r = a.scrollHeight, c = a.clientHeight;
  return [
    u,
    r,
    c
  ];
}, vx = function(a) {
  var u = a.scrollLeft, r = a.scrollWidth, c = a.clientWidth;
  return [
    u,
    r,
    c
  ];
}, tp = function(a, u) {
  return a === "v" ? fx(u) : dx(u);
}, ep = function(a, u) {
  return a === "v" ? mx(u) : vx(u);
}, hx = function(a, u) {
  return a === "h" && u === "rtl" ? -1 : 1;
}, gx = function(a, u, r, c, f) {
  var m = hx(a, window.getComputedStyle(u).direction), v = m * c, g = r.target, p = u.contains(g), y = !1, S = v > 0, d = 0, x = 0;
  do {
    if (!g)
      break;
    var C = ep(a, g), R = C[0], O = C[1], N = C[2], H = O - N - m * R;
    (R || H) && tp(a, g) && (d += H, x += R);
    var L = g.parentNode;
    g = L && L.nodeType === Node.DOCUMENT_FRAGMENT_NODE ? L.host : L;
  } while (
    // portaled content
    !p && g !== document.body || // self content
    p && (u.contains(g) || u === g)
  );
  return (S && Math.abs(d) < 1 || !S && Math.abs(x) < 1) && (y = !0), y;
}, Dr = function(a) {
  return "changedTouches" in a ? [a.changedTouches[0].clientX, a.changedTouches[0].clientY] : [0, 0];
}, U0 = function(a) {
  return [a.deltaX, a.deltaY];
}, H0 = function(a) {
  return a && "current" in a ? a.current : a;
}, yx = function(a, u) {
  return a[0] === u[0] && a[1] === u[1];
}, px = function(a) {
  return `
  .block-interactivity-`.concat(a, ` {pointer-events: none;}
  .allow-interactivity-`).concat(a, ` {pointer-events: all;}
`);
}, bx = 0, Ai = [];
function Sx(a) {
  var u = b.useRef([]), r = b.useRef([0, 0]), c = b.useRef(), f = b.useState(bx++)[0], m = b.useState(Py)[0], v = b.useRef(a);
  b.useEffect(function() {
    v.current = a;
  }, [a]), b.useEffect(function() {
    if (a.inert) {
      document.body.classList.add("block-interactivity-".concat(f));
      var O = VE([a.lockRef.current], (a.shards || []).map(H0), !0).filter(Boolean);
      return O.forEach(function(N) {
        return N.classList.add("allow-interactivity-".concat(f));
      }), function() {
        document.body.classList.remove("block-interactivity-".concat(f)), O.forEach(function(N) {
          return N.classList.remove("allow-interactivity-".concat(f));
        });
      };
    }
  }, [a.inert, a.lockRef.current, a.shards]);
  var g = b.useCallback(function(O, N) {
    if ("touches" in O && O.touches.length === 2 || O.type === "wheel" && O.ctrlKey)
      return !v.current.allowPinchZoom;
    var H = Dr(O), L = r.current, J = "deltaX" in O ? O.deltaX : L[0] - H[0], K = "deltaY" in O ? O.deltaY : L[1] - H[1], I, Z = O.target, X = Math.abs(J) > Math.abs(K) ? "h" : "v";
    if ("touches" in O && X === "h" && Z.type === "range")
      return !1;
    var Y = window.getSelection(), dt = Y && Y.anchorNode, ht = dt ? dt === Z || dt.contains(Z) : !1;
    if (ht)
      return !1;
    var xt = M0(X, Z);
    if (!xt)
      return !0;
    if (xt ? I = X : (I = X === "v" ? "h" : "v", xt = M0(X, Z)), !xt)
      return !1;
    if (!c.current && "changedTouches" in O && (J || K) && (c.current = I), !I)
      return !0;
    var st = c.current || I;
    return gx(st, N, O, st === "h" ? J : K);
  }, []), p = b.useCallback(function(O) {
    var N = O;
    if (!(!Ai.length || Ai[Ai.length - 1] !== m)) {
      var H = "deltaY" in N ? U0(N) : Dr(N), L = u.current.filter(function(I) {
        return I.name === N.type && (I.target === N.target || N.target === I.shadowParent) && yx(I.delta, H);
      })[0];
      if (L && L.should) {
        N.cancelable && N.preventDefault();
        return;
      }
      if (!L) {
        var J = (v.current.shards || []).map(H0).filter(Boolean).filter(function(I) {
          return I.contains(N.target);
        }), K = J.length > 0 ? g(N, J[0]) : !v.current.noIsolation;
        K && N.cancelable && N.preventDefault();
      }
    }
  }, []), y = b.useCallback(function(O, N, H, L) {
    var J = { name: O, delta: N, target: H, should: L, shadowParent: Ex(H) };
    u.current.push(J), setTimeout(function() {
      u.current = u.current.filter(function(K) {
        return K !== J;
      });
    }, 1);
  }, []), S = b.useCallback(function(O) {
    r.current = Dr(O), c.current = void 0;
  }, []), d = b.useCallback(function(O) {
    y(O.type, U0(O), O.target, g(O, a.lockRef.current));
  }, []), x = b.useCallback(function(O) {
    y(O.type, Dr(O), O.target, g(O, a.lockRef.current));
  }, []);
  b.useEffect(function() {
    return Ai.push(m), a.setCallbacks({
      onScrollCapture: d,
      onWheelCapture: d,
      onTouchMoveCapture: x
    }), document.addEventListener("wheel", p, _i), document.addEventListener("touchmove", p, _i), document.addEventListener("touchstart", S, _i), function() {
      Ai = Ai.filter(function(O) {
        return O !== m;
      }), document.removeEventListener("wheel", p, _i), document.removeEventListener("touchmove", p, _i), document.removeEventListener("touchstart", S, _i);
    };
  }, []);
  var C = a.removeScrollBar, R = a.inert;
  return b.createElement(
    b.Fragment,
    null,
    R ? b.createElement(m, { styles: px(f) }) : null,
    C ? b.createElement(cx, { noRelative: a.noRelative, gapMode: a.gapMode }) : null
  );
}
function Ex(a) {
  for (var u = null; a !== null; )
    a instanceof ShadowRoot && (u = a.host, a = a.host), a = a.parentNode;
  return u;
}
const xx = $E(Iy, Sx);
var np = b.forwardRef(function(a, u) {
  return b.createElement(Kr, Qn({}, a, { ref: u, sideCar: xx }));
});
np.classNames = Kr.classNames;
var Tx = function(a) {
  if (typeof document > "u")
    return null;
  var u = Array.isArray(a) ? a[0] : a;
  return u.ownerDocument.body;
}, Ri = /* @__PURE__ */ new WeakMap(), zr = /* @__PURE__ */ new WeakMap(), Mr = {}, Xf = 0, lp = function(a) {
  return a && (a.host || lp(a.parentNode));
}, wx = function(a, u) {
  return u.map(function(r) {
    if (a.contains(r))
      return r;
    var c = lp(r);
    return c && a.contains(c) ? c : (console.error("aria-hidden", r, "in not contained inside", a, ". Doing nothing"), null);
  }).filter(function(r) {
    return !!r;
  });
}, Cx = function(a, u, r, c) {
  var f = wx(u, Array.isArray(a) ? a : [a]);
  Mr[r] || (Mr[r] = /* @__PURE__ */ new WeakMap());
  var m = Mr[r], v = [], g = /* @__PURE__ */ new Set(), p = new Set(f), y = function(d) {
    !d || g.has(d) || (g.add(d), y(d.parentNode));
  };
  f.forEach(y);
  var S = function(d) {
    !d || p.has(d) || Array.prototype.forEach.call(d.children, function(x) {
      if (g.has(x))
        S(x);
      else
        try {
          var C = x.getAttribute(c), R = C !== null && C !== "false", O = (Ri.get(x) || 0) + 1, N = (m.get(x) || 0) + 1;
          Ri.set(x, O), m.set(x, N), v.push(x), O === 1 && R && zr.set(x, !0), N === 1 && x.setAttribute(r, "true"), R || x.setAttribute(c, "true");
        } catch (H) {
          console.error("aria-hidden: cannot operate on ", x, H);
        }
    });
  };
  return S(u), g.clear(), Xf++, function() {
    v.forEach(function(d) {
      var x = Ri.get(d) - 1, C = m.get(d) - 1;
      Ri.set(d, x), m.set(d, C), x || (zr.has(d) || d.removeAttribute(c), zr.delete(d)), C || d.removeAttribute(r);
    }), Xf--, Xf || (Ri = /* @__PURE__ */ new WeakMap(), Ri = /* @__PURE__ */ new WeakMap(), zr = /* @__PURE__ */ new WeakMap(), Mr = {});
  };
}, Ox = function(a, u, r) {
  r === void 0 && (r = "data-aria-hidden");
  var c = Array.from(Array.isArray(a) ? a : [a]), f = Tx(a);
  return f ? (c.push.apply(c, Array.from(f.querySelectorAll("[aria-live], script"))), Cx(c, f, r, "aria-hidden")) : function() {
    return null;
  };
}, _x = Object.defineProperty, pn = (a, u) => _x(a, "name", { value: u, configurable: !0 }), xd = "Dialog", [ap, XC] = /* @__PURE__ */ Qr(xd), [Ax, $n] = ap(xd), ip = /* @__PURE__ */ pn((a) => {
  const {
    __scopeDialog: u,
    children: r,
    open: c,
    defaultOpen: f,
    onOpenChange: m,
    modal: v = !0
  } = a, g = b.useRef(null), p = b.useRef(null), [y, S] = yd({
    prop: c,
    defaultProp: f ?? !1,
    onChange: m,
    caller: xd
  }), [d, x] = b.useState(0), [C, R] = b.useState(0);
  return /* @__PURE__ */ k.jsx(
    Ax,
    {
      scope: u,
      triggerRef: g,
      contentRef: p,
      contentId: An(),
      titleId: An(),
      descriptionId: An(),
      titlePresent: d > 0,
      descriptionPresent: C > 0,
      setTitleCount: x,
      setDescriptionCount: R,
      open: y,
      onOpenChange: S,
      onOpenToggle: b.useCallback(() => S((O) => !O), [S]),
      modal: v,
      children: r
    }
  );
}, "Dialog"), op = "DialogPortal", [Rx, up] = ap(op, {
  forceMount: void 0
}), rp = /* @__PURE__ */ pn((a) => {
  const { __scopeDialog: u, forceMount: r, children: c, container: f } = a, m = $n(op, u);
  return /* @__PURE__ */ k.jsx(Rx, { scope: u, forceMount: r, children: b.Children.map(c, (v) => /* @__PURE__ */ k.jsx(Fo, { present: r || m.open, children: /* @__PURE__ */ k.jsx(ky, { asChild: !0, container: f, children: v }) })) });
}, "DialogPortal"), od = "DialogOverlay", Td = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ pn(function(u, r) {
    const c = up(od, u.__scopeDialog), { forceMount: f = c.forceMount, ...m } = u, v = $n(od, u.__scopeDialog);
    return v.modal ? /* @__PURE__ */ k.jsx(Fo, { present: f || v.open, children: /* @__PURE__ */ k.jsx(Dx, { ...m, ref: r }) }) : null;
  }, "DialogOverlay")
), Nx = /* @__PURE__ */ kr("DialogOverlay.RemoveScroll"), Dx = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ pn(function(u, r) {
    const { __scopeDialog: c, ...f } = u, m = $n(od, c), v = Hy(), g = Fn(r, v);
    return (
      // Make sure `Content` is scrollable even when it doesn't live inside `RemoveScroll`
      // ie. when `Overlay` and `Content` are siblings
      /* @__PURE__ */ k.jsx(np, { as: Nx, allowPinchZoom: !0, shards: [m.contentRef], children: /* @__PURE__ */ k.jsx(
        se.div,
        {
          "data-state": Cd(m.open),
          ...f,
          ref: g,
          style: { pointerEvents: "auto", ...f.style }
        }
      ) })
    );
  }, "DialogOverlayImpl")
), Xo = "DialogContent", wd = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ pn(function(u, r) {
    const c = up(Xo, u.__scopeDialog), { forceMount: f = c.forceMount, ...m } = u, v = $n(Xo, u.__scopeDialog);
    return /* @__PURE__ */ k.jsx(Fo, { present: f || v.open, children: v.modal ? /* @__PURE__ */ k.jsx(zx, { ...m, ref: r }) : /* @__PURE__ */ k.jsx(Mx, { ...m, ref: r }) });
  }, "DialogContent")
), zx = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ pn(function(u, r) {
    const c = $n(Xo, u.__scopeDialog), f = b.useRef(null), m = Fn(r, c.contentRef, f);
    return b.useEffect(() => {
      const v = f.current;
      if (v) return Ox(v);
    }, []), /* @__PURE__ */ k.jsx(
      cp,
      {
        ...u,
        ref: m,
        trapFocus: c.open,
        disableOutsidePointerEvents: c.open,
        onCloseAutoFocus: ke(u.onCloseAutoFocus, (v) => {
          var g;
          v.preventDefault(), (g = c.triggerRef.current) == null || g.focus();
        }),
        onPointerDownOutside: ke(u.onPointerDownOutside, (v) => {
          const g = v.detail.originalEvent, p = g.button === 0 && g.ctrlKey === !0;
          (g.button === 2 || p) && v.preventDefault();
        }),
        onFocusOutside: ke(
          u.onFocusOutside,
          (v) => v.preventDefault()
        )
      }
    );
  }, "DialogContentModal")
), Mx = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ pn(function(u, r) {
    const c = $n(Xo, u.__scopeDialog), f = b.useRef(!1), m = b.useRef(!1);
    return /* @__PURE__ */ k.jsx(
      cp,
      {
        ...u,
        ref: r,
        trapFocus: !1,
        disableOutsidePointerEvents: !1,
        onCloseAutoFocus: (v) => {
          var g, p;
          (g = u.onCloseAutoFocus) == null || g.call(u, v), v.defaultPrevented || (f.current || (p = c.triggerRef.current) == null || p.focus(), v.preventDefault()), f.current = !1, m.current = !1;
        },
        onInteractOutside: (v) => {
          var y, S;
          (y = u.onInteractOutside) == null || y.call(u, v), v.defaultPrevented || (f.current = !0, v.detail.originalEvent.type === "pointerdown" && (m.current = !0));
          const g = v.target;
          ((S = c.triggerRef.current) == null ? void 0 : S.contains(g)) && v.preventDefault(), v.detail.originalEvent.type === "focusin" && m.current && v.preventDefault();
        }
      }
    );
  }, "DialogContentNonModal")
), cp = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ pn(function(u, r) {
    const { __scopeDialog: c, trapFocus: f, onOpenAutoFocus: m, onCloseAutoFocus: v, ...g } = u, p = $n(Xo, c);
    return Ed(), /* @__PURE__ */ k.jsx(k.Fragment, { children: /* @__PURE__ */ k.jsx(
      HE,
      {
        asChild: !0,
        loop: !0,
        trapped: f,
        onMountAutoFocus: m,
        onUnmountAutoFocus: v,
        children: /* @__PURE__ */ k.jsx(
          Uy,
          {
            role: "dialog",
            id: p.contentId,
            "aria-describedby": p.descriptionPresent ? p.descriptionId : void 0,
            "aria-labelledby": p.titlePresent ? p.titleId : void 0,
            "data-state": Cd(p.open),
            ...g,
            ref: r,
            deferPointerDownOutside: !0,
            onDismiss: () => p.onOpenChange(!1)
          }
        )
      }
    ) });
  }, "DialogContentImpl")
), Ux = "DialogTitle", sp = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ pn(function(u, r) {
    const { __scopeDialog: c, ...f } = u, m = $n(Ux, c), { setTitleCount: v } = m;
    return ln(() => (v((g) => g + 1), () => v((g) => g - 1)), [v]), /* @__PURE__ */ k.jsx(se.h2, { id: m.titleId, ...f, ref: r });
  }, "DialogTitle")
), Hx = "DialogDescription", fp = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ pn(function(u, r) {
    const { __scopeDialog: c, ...f } = u, m = $n(Hx, c), { setDescriptionCount: v } = m;
    return ln(() => (v((g) => g + 1), () => v((g) => g - 1)), [v]), /* @__PURE__ */ k.jsx(se.p, { id: m.descriptionId, ...f, ref: r });
  }, "DialogDescription")
), jx = "DialogClose", Bx = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ pn(function(u, r) {
    const { __scopeDialog: c, ...f } = u, m = $n(jx, c);
    return /* @__PURE__ */ k.jsx(
      se.button,
      {
        type: "button",
        ...f,
        ref: r,
        onClick: ke(u.onClick, () => m.onOpenChange(!1))
      }
    );
  }, "DialogClose")
);
function Cd(a) {
  return a ? "open" : "closed";
}
pn(Cd, "getState");
var Vo = '[cmdk-group=""]', kf = '[cmdk-group-items=""]', Lx = '[cmdk-group-heading=""]', dp = '[cmdk-item=""]', j0 = `${dp}:not([aria-disabled="true"])`, ud = "cmdk-item-select", Di = "data-value", Yx = (a, u, r) => sE(a, u, r), mp = b.createContext(void 0), $o = () => b.useContext(mp), vp = b.createContext(void 0), Od = () => b.useContext(vp), hp = b.createContext(void 0), gp = b.forwardRef((a, u) => {
  let r = zi(() => {
    var Q, rt;
    return { search: "", value: (rt = (Q = a.value) != null ? Q : a.defaultValue) != null ? rt : "", selectedItemId: void 0, filtered: { count: 0, items: /* @__PURE__ */ new Map(), groups: /* @__PURE__ */ new Set() } };
  }), c = zi(() => /* @__PURE__ */ new Set()), f = zi(() => /* @__PURE__ */ new Map()), m = zi(() => /* @__PURE__ */ new Map()), v = zi(() => /* @__PURE__ */ new Set()), g = yp(a), { label: p, children: y, value: S, onValueChange: d, filter: x, shouldFilter: C, loop: R, disablePointerSelection: O = !1, vimBindings: N = !0, ...H } = a, L = An(), J = An(), K = An(), I = b.useRef(null), Z = $x();
  Da(() => {
    if (S !== void 0) {
      let Q = S.trim();
      r.current.value = Q, X.emit();
    }
  }, [S]), Da(() => {
    Z(6, Tt);
  }, []);
  let X = b.useMemo(() => ({ subscribe: (Q) => (v.current.add(Q), () => v.current.delete(Q)), snapshot: () => r.current, setState: (Q, rt, E) => {
    var _, V, $, ft;
    if (!Object.is(r.current[Q], rt)) {
      if (r.current[Q] = rt, Q === "search") st(), ht(), Z(1, xt);
      else if (Q === "value") {
        if (document.activeElement.hasAttribute("cmdk-input") || document.activeElement.hasAttribute("cmdk-root")) {
          let W = document.getElementById(K);
          W ? W.focus() : (_ = document.getElementById(L)) == null || _.focus();
        }
        if (Z(7, () => {
          var W;
          r.current.selectedItemId = (W = gt()) == null ? void 0 : W.id, X.emit();
        }), E || Z(5, Tt), ((V = g.current) == null ? void 0 : V.value) !== void 0) {
          let W = rt ?? "";
          (ft = ($ = g.current).onValueChange) == null || ft.call($, W);
          return;
        }
      }
      X.emit();
    }
  }, emit: () => {
    v.current.forEach((Q) => Q());
  } }), []), Y = b.useMemo(() => ({ value: (Q, rt, E) => {
    var _;
    rt !== ((_ = m.current.get(Q)) == null ? void 0 : _.value) && (m.current.set(Q, { value: rt, keywords: E }), r.current.filtered.items.set(Q, dt(rt, E)), Z(2, () => {
      ht(), X.emit();
    }));
  }, item: (Q, rt) => (c.current.add(Q), rt && (f.current.has(rt) ? f.current.get(rt).add(Q) : f.current.set(rt, /* @__PURE__ */ new Set([Q]))), Z(3, () => {
    st(), ht(), r.current.value || xt(), X.emit();
  }), () => {
    m.current.delete(Q), c.current.delete(Q), r.current.filtered.items.delete(Q);
    let E = gt();
    Z(4, () => {
      st(), (E == null ? void 0 : E.getAttribute("id")) === Q && xt(), X.emit();
    });
  }), group: (Q) => (f.current.has(Q) || f.current.set(Q, /* @__PURE__ */ new Set()), () => {
    m.current.delete(Q), f.current.delete(Q);
  }), filter: () => g.current.shouldFilter, label: p || a["aria-label"], getDisablePointerSelection: () => g.current.disablePointerSelection, listId: L, inputId: K, labelId: J, listInnerRef: I }), []);
  function dt(Q, rt) {
    var E, _;
    let V = (_ = (E = g.current) == null ? void 0 : E.filter) != null ? _ : Yx;
    return Q ? V(Q, r.current.search, rt) : 0;
  }
  function ht() {
    if (!r.current.search || g.current.shouldFilter === !1) return;
    let Q = r.current.filtered.items, rt = [];
    r.current.filtered.groups.forEach((_) => {
      let V = f.current.get(_), $ = 0;
      V.forEach((ft) => {
        let W = Q.get(ft);
        $ = Math.max(W, $);
      }), rt.push([_, $]);
    });
    let E = I.current;
    yt().sort((_, V) => {
      var $, ft;
      let W = _.getAttribute("id"), bt = V.getAttribute("id");
      return (($ = Q.get(bt)) != null ? $ : 0) - ((ft = Q.get(W)) != null ? ft : 0);
    }).forEach((_) => {
      let V = _.closest(kf);
      V ? V.appendChild(_.parentElement === V ? _ : _.closest(`${kf} > *`)) : E.appendChild(_.parentElement === E ? _ : _.closest(`${kf} > *`));
    }), rt.sort((_, V) => V[1] - _[1]).forEach((_) => {
      var V;
      let $ = (V = I.current) == null ? void 0 : V.querySelector(`${Vo}[${Di}="${encodeURIComponent(_[0])}"]`);
      $ == null || $.parentElement.appendChild($);
    });
  }
  function xt() {
    let Q = yt().find((E) => E.getAttribute("aria-disabled") !== "true"), rt = Q == null ? void 0 : Q.getAttribute(Di);
    X.setState("value", rt || void 0);
  }
  function st() {
    var Q, rt, E, _;
    if (!r.current.search || g.current.shouldFilter === !1) {
      r.current.filtered.count = c.current.size;
      return;
    }
    r.current.filtered.groups = /* @__PURE__ */ new Set();
    let V = 0;
    for (let $ of c.current) {
      let ft = (rt = (Q = m.current.get($)) == null ? void 0 : Q.value) != null ? rt : "", W = (_ = (E = m.current.get($)) == null ? void 0 : E.keywords) != null ? _ : [], bt = dt(ft, W);
      r.current.filtered.items.set($, bt), bt > 0 && V++;
    }
    for (let [$, ft] of f.current) for (let W of ft) if (r.current.filtered.items.get(W) > 0) {
      r.current.filtered.groups.add($);
      break;
    }
    r.current.filtered.count = V;
  }
  function Tt() {
    var Q, rt, E;
    let _ = gt();
    _ && (((Q = _.parentElement) == null ? void 0 : Q.firstChild) === _ && ((E = (rt = _.closest(Vo)) == null ? void 0 : rt.querySelector(Lx)) == null || E.scrollIntoView({ block: "nearest" })), _.scrollIntoView({ block: "nearest" }));
  }
  function gt() {
    var Q;
    return (Q = I.current) == null ? void 0 : Q.querySelector(`${dp}[aria-selected="true"]`);
  }
  function yt() {
    var Q;
    return Array.from(((Q = I.current) == null ? void 0 : Q.querySelectorAll(j0)) || []);
  }
  function B(Q) {
    let rt = yt()[Q];
    rt && X.setState("value", rt.getAttribute(Di));
  }
  function tt(Q) {
    var rt;
    let E = gt(), _ = yt(), V = _.findIndex((ft) => ft === E), $ = _[V + Q];
    (rt = g.current) != null && rt.loop && ($ = V + Q < 0 ? _[_.length - 1] : V + Q === _.length ? _[0] : _[V + Q]), $ && X.setState("value", $.getAttribute(Di));
  }
  function P(Q) {
    let rt = gt(), E = rt == null ? void 0 : rt.closest(Vo), _;
    for (; E && !_; ) E = Q > 0 ? Jx(E, Vo) : Fx(E, Vo), _ = E == null ? void 0 : E.querySelector(j0);
    _ ? X.setState("value", _.getAttribute(Di)) : tt(Q);
  }
  let at = () => B(yt().length - 1), F = (Q) => {
    Q.preventDefault(), Q.metaKey ? at() : Q.altKey ? P(1) : tt(1);
  }, Bt = (Q) => {
    Q.preventDefault(), Q.metaKey ? B(0) : Q.altKey ? P(-1) : tt(-1);
  };
  return b.createElement(se.div, { ref: u, tabIndex: -1, ...H, "cmdk-root": "", onKeyDown: (Q) => {
    var rt;
    (rt = H.onKeyDown) == null || rt.call(H, Q);
    let E = Q.nativeEvent.isComposing || Q.keyCode === 229;
    if (!(Q.defaultPrevented || E)) switch (Q.key) {
      case "n":
      case "j": {
        N && Q.ctrlKey && F(Q);
        break;
      }
      case "ArrowDown": {
        F(Q);
        break;
      }
      case "p":
      case "k": {
        N && Q.ctrlKey && Bt(Q);
        break;
      }
      case "ArrowUp": {
        Bt(Q);
        break;
      }
      case "Home": {
        Q.preventDefault(), B(0);
        break;
      }
      case "End": {
        Q.preventDefault(), at();
        break;
      }
      case "Enter": {
        Q.preventDefault();
        let _ = gt();
        if (_) {
          let V = new Event(ud);
          _.dispatchEvent(V);
        }
      }
    }
  } }, b.createElement("label", { "cmdk-label": "", htmlFor: Y.inputId, id: Y.labelId, style: Px }, p), Jr(a, (Q) => b.createElement(vp.Provider, { value: X }, b.createElement(mp.Provider, { value: Y }, Q))));
}), qx = b.forwardRef((a, u) => {
  var r, c;
  let f = An(), m = b.useRef(null), v = b.useContext(hp), g = $o(), p = yp(a), y = (c = (r = p.current) == null ? void 0 : r.forceMount) != null ? c : v == null ? void 0 : v.forceMount;
  Da(() => {
    if (!y) return g.item(f, v == null ? void 0 : v.id);
  }, [y]);
  let S = pp(f, m, [a.value, a.children, m], a.keywords), d = Od(), x = Il((Z) => Z.value && Z.value === S.current), C = Il((Z) => y || g.filter() === !1 ? !0 : Z.search ? Z.filtered.items.get(f) > 0 : !0);
  b.useEffect(() => {
    let Z = m.current;
    if (!(!Z || a.disabled)) return Z.addEventListener(ud, R), () => Z.removeEventListener(ud, R);
  }, [C, a.onSelect, a.disabled]);
  function R() {
    var Z, X;
    O(), (X = (Z = p.current).onSelect) == null || X.call(Z, S.current);
  }
  function O() {
    d.setState("value", S.current, !0);
  }
  if (!C) return null;
  let { disabled: N, value: H, onSelect: L, forceMount: J, keywords: K, ...I } = a;
  return b.createElement(se.div, { ref: Ra(m, u), ...I, id: f, "cmdk-item": "", role: "option", "aria-disabled": !!N, "aria-selected": !!x, "data-disabled": !!N, "data-selected": !!x, onPointerMove: N || g.getDisablePointerSelection() ? void 0 : O, onClick: N ? void 0 : R }, a.children);
}), Vx = b.forwardRef((a, u) => {
  let { heading: r, children: c, forceMount: f, ...m } = a, v = An(), g = b.useRef(null), p = b.useRef(null), y = An(), S = $o(), d = Il((C) => f || S.filter() === !1 ? !0 : C.search ? C.filtered.groups.has(v) : !0);
  Da(() => S.group(v), []), pp(v, g, [a.value, a.heading, p]);
  let x = b.useMemo(() => ({ id: v, forceMount: f }), [f]);
  return b.createElement(se.div, { ref: Ra(g, u), ...m, "cmdk-group": "", role: "presentation", hidden: d ? void 0 : !0 }, r && b.createElement("div", { ref: p, "cmdk-group-heading": "", "aria-hidden": !0, id: y }, r), Jr(a, (C) => b.createElement("div", { "cmdk-group-items": "", role: "group", "aria-labelledby": r ? y : void 0 }, b.createElement(hp.Provider, { value: x }, C))));
}), Gx = b.forwardRef((a, u) => {
  let { alwaysRender: r, ...c } = a, f = b.useRef(null), m = Il((v) => !v.search);
  return !r && !m ? null : b.createElement(se.div, { ref: Ra(f, u), ...c, "cmdk-separator": "", role: "separator" });
}), Xx = b.forwardRef((a, u) => {
  let { onValueChange: r, ...c } = a, f = a.value != null, m = Od(), v = Il((y) => y.search), g = Il((y) => y.selectedItemId), p = $o();
  return b.useEffect(() => {
    a.value != null && m.setState("search", a.value);
  }, [a.value]), b.createElement(se.input, { ref: u, ...c, "cmdk-input": "", autoComplete: "off", autoCorrect: "off", spellCheck: !1, "aria-autocomplete": "list", role: "combobox", "aria-expanded": !0, "aria-controls": p.listId, "aria-labelledby": p.labelId, "aria-activedescendant": g, id: p.inputId, type: "text", value: f ? a.value : v, onChange: (y) => {
    f || m.setState("search", y.target.value), r == null || r(y.target.value);
  } });
}), kx = b.forwardRef((a, u) => {
  let { children: r, label: c = "Suggestions", ...f } = a, m = b.useRef(null), v = b.useRef(null), g = Il((y) => y.selectedItemId), p = $o();
  return b.useEffect(() => {
    if (v.current && m.current) {
      let y = v.current, S = m.current, d, x = new ResizeObserver(() => {
        d = requestAnimationFrame(() => {
          let C = y.offsetHeight;
          S.style.setProperty("--cmdk-list-height", C.toFixed(1) + "px");
        });
      });
      return x.observe(y), () => {
        cancelAnimationFrame(d), x.unobserve(y);
      };
    }
  }, []), b.createElement(se.div, { ref: Ra(m, u), ...f, "cmdk-list": "", role: "listbox", tabIndex: -1, "aria-activedescendant": g, "aria-label": c, id: p.listId }, Jr(a, (y) => b.createElement("div", { ref: Ra(v, p.listInnerRef), "cmdk-list-sizer": "" }, y)));
}), Qx = b.forwardRef((a, u) => {
  let { open: r, onOpenChange: c, overlayClassName: f, contentClassName: m, container: v, ...g } = a;
  return b.createElement(ip, { open: r, onOpenChange: c }, b.createElement(rp, { container: v }, b.createElement(Td, { "cmdk-overlay": "", className: f }), b.createElement(wd, { "aria-label": a.label, "cmdk-dialog": "", className: m }, b.createElement(gp, { ref: u, ...g }))));
}), Zx = b.forwardRef((a, u) => Il((r) => r.filtered.count === 0) ? b.createElement(se.div, { ref: u, ...a, "cmdk-empty": "", role: "presentation" }) : null), Kx = b.forwardRef((a, u) => {
  let { progress: r, children: c, label: f = "Loading...", ...m } = a;
  return b.createElement(se.div, { ref: u, ...m, "cmdk-loading": "", role: "progressbar", "aria-valuenow": r, "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": f }, Jr(a, (v) => b.createElement("div", { "aria-hidden": !0 }, v)));
}), Ke = Object.assign(gp, { List: kx, Item: qx, Input: Xx, Group: Vx, Separator: Gx, Dialog: Qx, Empty: Zx, Loading: Kx });
function Jx(a, u) {
  let r = a.nextElementSibling;
  for (; r; ) {
    if (r.matches(u)) return r;
    r = r.nextElementSibling;
  }
}
function Fx(a, u) {
  let r = a.previousElementSibling;
  for (; r; ) {
    if (r.matches(u)) return r;
    r = r.previousElementSibling;
  }
}
function yp(a) {
  let u = b.useRef(a);
  return Da(() => {
    u.current = a;
  }), u;
}
var Da = typeof window > "u" ? b.useEffect : b.useLayoutEffect;
function zi(a) {
  let u = b.useRef();
  return u.current === void 0 && (u.current = a()), u;
}
function Il(a) {
  let u = Od(), r = () => a(u.snapshot());
  return b.useSyncExternalStore(u.subscribe, r, r);
}
function pp(a, u, r, c = []) {
  let f = b.useRef(), m = $o();
  return Da(() => {
    var v;
    let g = (() => {
      var y;
      for (let S of r) {
        if (typeof S == "string") return S.trim();
        if (typeof S == "object" && "current" in S) return S.current ? (y = S.current.textContent) == null ? void 0 : y.trim() : f.current;
      }
    })(), p = c.map((y) => y.trim());
    m.value(a, g, p), (v = u.current) == null || v.setAttribute(Di, g), f.current = g;
  }), f;
}
var $x = () => {
  let [a, u] = b.useState(), r = zi(() => /* @__PURE__ */ new Map());
  return Da(() => {
    r.current.forEach((c) => c()), r.current = /* @__PURE__ */ new Map();
  }, [a]), (c, f) => {
    r.current.set(c, f), u({});
  };
};
function Ix(a) {
  let u = a.type;
  return typeof u == "function" ? u(a.props) : "render" in u ? u.render(a.props) : a;
}
function Jr({ asChild: a, children: u }, r) {
  return a && b.isValidElement(u) ? b.cloneElement(Ix(u), { ref: u.ref }, r(u.props.children)) : r(u);
}
var Px = { position: "absolute", width: "1px", height: "1px", padding: "0", margin: "-1px", overflow: "hidden", clip: "rect(0, 0, 0, 0)", whiteSpace: "nowrap", borderWidth: "0" };
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Wx = (a) => a.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(), bp = (...a) => a.filter((u, r, c) => !!u && u.trim() !== "" && c.indexOf(u) === r).join(" ").trim();
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
var tT = {
  xmlns: "http://www.w3.org/2000/svg",
  width: 24,
  height: 24,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round"
};
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const eT = b.forwardRef(
  ({
    color: a = "currentColor",
    size: u = 24,
    strokeWidth: r = 2,
    absoluteStrokeWidth: c,
    className: f = "",
    children: m,
    iconNode: v,
    ...g
  }, p) => b.createElement(
    "svg",
    {
      ref: p,
      ...tT,
      width: u,
      height: u,
      stroke: a,
      strokeWidth: c ? Number(r) * 24 / Number(u) : r,
      className: bp("lucide", f),
      ...g
    },
    [
      ...v.map(([y, S]) => b.createElement(y, S)),
      ...Array.isArray(m) ? m : [m]
    ]
  )
);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Oe = (a, u) => {
  const r = b.forwardRef(
    ({ className: c, ...f }, m) => b.createElement(eT, {
      ref: m,
      iconNode: u,
      className: bp(`lucide-${Wx(a)}`, c),
      ...f
    })
  );
  return r.displayName = `${a}`, r;
};
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const nT = Oe("ArrowUpRight", [
  ["path", { d: "M7 7h10v10", key: "1tivn9" }],
  ["path", { d: "M7 17 17 7", key: "1vkiza" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const lT = Oe("CreditCard", [
  ["rect", { width: "20", height: "14", x: "2", y: "5", rx: "2", key: "ynyp8z" }],
  ["line", { x1: "2", x2: "22", y1: "10", y2: "10", key: "1b3vmo" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const aT = Oe("DatabaseBackup", [
  ["ellipse", { cx: "12", cy: "5", rx: "9", ry: "3", key: "msslwz" }],
  ["path", { d: "M3 12a9 3 0 0 0 5 2.69", key: "1ui2ym" }],
  ["path", { d: "M21 9.3V5", key: "6k6cib" }],
  ["path", { d: "M3 5v14a9 3 0 0 0 6.47 2.88", key: "i62tjy" }],
  ["path", { d: "M12 12v4h4", key: "1bxaet" }],
  [
    "path",
    {
      d: "M13 20a5 5 0 0 0 9-3 4.5 4.5 0 0 0-4.5-4.5c-1.33 0-2.54.54-3.41 1.41L12 16",
      key: "1f4ei9"
    }
  ]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const iT = Oe("Handshake", [
  ["path", { d: "m11 17 2 2a1 1 0 1 0 3-3", key: "efffak" }],
  [
    "path",
    {
      d: "m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4",
      key: "9pr0kb"
    }
  ],
  ["path", { d: "m21 3 1 11h-2", key: "1tisrp" }],
  ["path", { d: "M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3", key: "1uvwmv" }],
  ["path", { d: "M3 4h8", key: "1ep09j" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const oT = Oe("LayoutDashboard", [
  ["rect", { width: "7", height: "9", x: "3", y: "3", rx: "1", key: "10lvy0" }],
  ["rect", { width: "7", height: "5", x: "14", y: "3", rx: "1", key: "16une8" }],
  ["rect", { width: "7", height: "9", x: "14", y: "12", rx: "1", key: "1hutg5" }],
  ["rect", { width: "7", height: "5", x: "3", y: "16", rx: "1", key: "ldoo1y" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const uT = Oe("LifeBuoy", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["path", { d: "m4.93 4.93 4.24 4.24", key: "1ymg45" }],
  ["path", { d: "m14.83 9.17 4.24-4.24", key: "1cb5xl" }],
  ["path", { d: "m14.83 14.83 4.24 4.24", key: "q42g0n" }],
  ["path", { d: "m9.17 14.83-4.24 4.24", key: "bqpfvv" }],
  ["circle", { cx: "12", cy: "12", r: "4", key: "4exip2" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const rT = Oe("Megaphone", [
  ["path", { d: "m3 11 18-5v12L3 14v-3z", key: "n962bs" }],
  ["path", { d: "M11.6 16.8a3 3 0 1 1-5.8-1.6", key: "1yl0tm" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const cT = Oe("MessagesSquare", [
  ["path", { d: "M14 9a2 2 0 0 1-2 2H6l-4 4V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2z", key: "p1xzt8" }],
  ["path", { d: "M18 9h2a2 2 0 0 1 2 2v11l-4-4h-6a2 2 0 0 1-2-2v-1", key: "1cx29u" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const sT = Oe("Newspaper", [
  [
    "path",
    {
      d: "M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2",
      key: "7pis2x"
    }
  ],
  ["path", { d: "M18 14h-8", key: "sponae" }],
  ["path", { d: "M15 18h-5", key: "95g1m2" }],
  ["path", { d: "M10 6h8v4h-8V6Z", key: "smlsk5" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const fT = Oe("Receipt", [
  [
    "path",
    { d: "M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z", key: "q3az6g" }
  ],
  ["path", { d: "M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8", key: "1h4pet" }],
  ["path", { d: "M12 17.5v-11", key: "1jc1ny" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Sp = Oe("Search", [
  ["circle", { cx: "11", cy: "11", r: "8", key: "4ej97u" }],
  ["path", { d: "m21 21-4.3-4.3", key: "1qie3q" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const dT = Oe("Send", [
  [
    "path",
    {
      d: "M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z",
      key: "1ffxy3"
    }
  ],
  ["path", { d: "m21.854 2.147-10.94 10.939", key: "12cjpa" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const mT = Oe("Settings", [
  [
    "path",
    {
      d: "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z",
      key: "1qme2f"
    }
  ],
  ["circle", { cx: "12", cy: "12", r: "3", key: "1v7zrd" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const vT = Oe("TicketPercent", [
  [
    "path",
    {
      d: "M2 9a3 3 0 1 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 1 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z",
      key: "1l48ns"
    }
  ],
  ["path", { d: "M9 9h.01", key: "1q5me6" }],
  ["path", { d: "m15 9-6 6", key: "1uzhvr" }],
  ["path", { d: "M15 15h.01", key: "lqbp3k" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const hT = Oe("Users", [
  ["path", { d: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", key: "1yyitq" }],
  ["circle", { cx: "9", cy: "7", r: "4", key: "nufk8" }],
  ["path", { d: "M22 21v-2a4 4 0 0 0-3-3.87", key: "kshegd" }],
  ["path", { d: "M16 3.13a4 4 0 0 1 0 7.75", key: "1da9ce" }]
]);
/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const gT = Oe("X", [
  ["path", { d: "M18 6 6 18", key: "1bl5f8" }],
  ["path", { d: "m6 6 12 12", key: "d8bk6v" }]
]), Ep = ip, yT = rp, xp = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  Td,
  {
    ref: r,
    className: Ze(
      "fixed inset-0 z-50 bg-black/80  data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      a
    ),
    ...u
  }
));
xp.displayName = Td.displayName;
const _d = b.forwardRef(({ className: a, children: u, ...r }, c) => /* @__PURE__ */ k.jsxs(yT, { children: [
  /* @__PURE__ */ k.jsx(xp, {}),
  /* @__PURE__ */ k.jsxs(
    wd,
    {
      ref: c,
      className: Ze(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
        a
      ),
      ...r,
      children: [
        u,
        /* @__PURE__ */ k.jsxs(Bx, { className: "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground", children: [
          /* @__PURE__ */ k.jsx(gT, { className: "h-4 w-4" }),
          /* @__PURE__ */ k.jsx("span", { className: "sr-only", children: "Закрыть" })
        ] })
      ]
    }
  )
] }));
_d.displayName = wd.displayName;
const Tp = ({
  className: a,
  ...u
}) => /* @__PURE__ */ k.jsx(
  "div",
  {
    className: Ze(
      "flex flex-col space-y-1.5 text-center sm:text-left",
      a
    ),
    ...u
  }
);
Tp.displayName = "DialogHeader";
const wp = ({
  className: a,
  ...u
}) => /* @__PURE__ */ k.jsx(
  "div",
  {
    className: Ze(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      a
    ),
    ...u
  }
);
wp.displayName = "DialogFooter";
const Ad = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  sp,
  {
    ref: r,
    className: Ze(
      "text-lg font-semibold leading-none tracking-tight",
      a
    ),
    ...u
  }
));
Ad.displayName = sp.displayName;
const Rd = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  fp,
  {
    ref: r,
    className: Ze("text-sm text-muted-foreground", a),
    ...u
  }
));
Rd.displayName = fp.displayName;
const Cp = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  Ke,
  {
    ref: r,
    className: Ze(
      "flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground",
      a
    ),
    ...u
  }
));
Cp.displayName = Ke.displayName;
const pT = ({ children: a, title: u = "Поиск", description: r = "Найдите раздел", ...c }) => /* @__PURE__ */ k.jsx(Ep, { ...c, children: /* @__PURE__ */ k.jsxs(_d, { className: "overflow-hidden p-0", children: [
  /* @__PURE__ */ k.jsx(Ad, { className: "sr-only", children: u }),
  /* @__PURE__ */ k.jsx(Rd, { className: "sr-only", children: r }),
  /* @__PURE__ */ k.jsx(Cp, { className: "[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5", children: a })
] }) }), Op = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsxs("div", { className: "flex items-center border-b px-3", "cmdk-input-wrapper": "", children: [
  /* @__PURE__ */ k.jsx(Sp, { className: "mr-2 h-4 w-4 shrink-0 opacity-50" }),
  /* @__PURE__ */ k.jsx(
    Ke.Input,
    {
      ref: r,
      className: Ze(
        "flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
        a
      ),
      ...u
    }
  )
] }));
Op.displayName = Ke.Input.displayName;
const _p = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  Ke.List,
  {
    ref: r,
    className: Ze("max-h-[300px] overflow-y-auto overflow-x-hidden", a),
    ...u
  }
));
_p.displayName = Ke.List.displayName;
const Ap = b.forwardRef((a, u) => /* @__PURE__ */ k.jsx(
  Ke.Empty,
  {
    ref: u,
    className: "py-6 text-center text-sm",
    ...a
  }
));
Ap.displayName = Ke.Empty.displayName;
const Rp = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  Ke.Group,
  {
    ref: r,
    className: Ze(
      "overflow-hidden p-1 text-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground",
      a
    ),
    ...u
  }
));
Rp.displayName = Ke.Group.displayName;
const bT = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  Ke.Separator,
  {
    ref: r,
    className: Ze("-mx-1 h-px bg-border", a),
    ...u
  }
));
bT.displayName = Ke.Separator.displayName;
const Np = b.forwardRef(({ className: a, ...u }, r) => /* @__PURE__ */ k.jsx(
  Ke.Item,
  {
    ref: r,
    className: Ze(
      "relative flex cursor-default gap-2 select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none data-[disabled=true]:pointer-events-none data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground data-[disabled=true]:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
      a
    ),
    ...u
  }
));
Np.displayName = Ke.Item.displayName;
const ST = ["top", "right", "bottom", "left"], Pl = Math.min, gl = Math.max, qr = Math.round, Ur = Math.floor, yl = (a) => ({
  x: a,
  y: a
}), ET = {
  left: "right",
  right: "left",
  bottom: "top",
  top: "bottom"
};
function Dp(a, u, r) {
  return gl(a, Pl(u, r));
}
function bl(a, u) {
  return typeof a == "function" ? a(u) : a;
}
function Wl(a) {
  return a.split("-")[0];
}
function ji(a) {
  return a.split("-")[1];
}
function Nd(a) {
  return a === "x" ? "y" : "x";
}
function Dd(a) {
  return a === "y" ? "height" : "width";
}
function Zn(a) {
  const u = a[0];
  return u === "t" || u === "b" ? "y" : "x";
}
function zd(a) {
  return Nd(Zn(a));
}
function xT(a, u, r) {
  r === void 0 && (r = !1);
  const c = ji(a), f = zd(a), m = Dd(f);
  let v = f === "x" ? c === (r ? "end" : "start") ? "right" : "left" : c === "start" ? "bottom" : "top";
  return u.reference[m] > u.floating[m] && (v = Vr(v)), [v, Vr(v)];
}
function TT(a) {
  const u = Vr(a);
  return [rd(a), u, rd(u)];
}
function rd(a) {
  return a.includes("start") ? a.replace("start", "end") : a.replace("end", "start");
}
const B0 = ["left", "right"], L0 = ["right", "left"], wT = ["top", "bottom"], CT = ["bottom", "top"];
function OT(a, u, r) {
  switch (a) {
    case "top":
    case "bottom":
      return r ? u ? L0 : B0 : u ? B0 : L0;
    case "left":
    case "right":
      return u ? wT : CT;
    default:
      return [];
  }
}
function _T(a, u, r, c) {
  const f = ji(a);
  let m = OT(Wl(a), r === "start", c);
  return f && (m = m.map((v) => v + "-" + f), u && (m = m.concat(m.map(rd)))), m;
}
function Vr(a) {
  const u = Wl(a);
  return ET[u] + a.slice(u.length);
}
function AT(a) {
  var u, r, c, f;
  return {
    top: (u = a.top) != null ? u : 0,
    right: (r = a.right) != null ? r : 0,
    bottom: (c = a.bottom) != null ? c : 0,
    left: (f = a.left) != null ? f : 0
  };
}
function zp(a) {
  return typeof a != "number" ? AT(a) : {
    top: a,
    right: a,
    bottom: a,
    left: a
  };
}
function Gr(a) {
  const {
    x: u,
    y: r,
    width: c,
    height: f
  } = a;
  return {
    width: c,
    height: f,
    top: r,
    left: u,
    right: u + c,
    bottom: r + f,
    x: u,
    y: r
  };
}
function Y0(a, u, r) {
  let {
    reference: c,
    floating: f
  } = a;
  const m = Zn(u), v = zd(u), g = Dd(v), p = Wl(u), y = m === "y", S = c.x + c.width / 2 - f.width / 2, d = c.y + c.height / 2 - f.height / 2, x = c[g] / 2 - f[g] / 2;
  let C;
  switch (p) {
    case "top":
      C = {
        x: S,
        y: c.y - f.height
      };
      break;
    case "bottom":
      C = {
        x: S,
        y: c.y + c.height
      };
      break;
    case "right":
      C = {
        x: c.x + c.width,
        y: d
      };
      break;
    case "left":
      C = {
        x: c.x - f.width,
        y: d
      };
      break;
    default:
      C = {
        x: c.x,
        y: c.y
      };
  }
  const R = ji(u);
  return R && (C[v] += x * (R === "end" ? 1 : -1) * (r && y ? -1 : 1)), C;
}
async function RT(a, u) {
  var r;
  u === void 0 && (u = {});
  const {
    x: c,
    y: f,
    platform: m,
    rects: v,
    elements: g,
    strategy: p
  } = a, {
    boundary: y = "clippingAncestors",
    rootBoundary: S = "viewport",
    elementContext: d = "floating",
    altBoundary: x = !1,
    padding: C = 0
  } = bl(u, a), R = zp(C), N = g[x ? d === "floating" ? "reference" : "floating" : d], H = Gr(await m.getClippingRect({
    element: (r = await (m.isElement == null ? void 0 : m.isElement(N))) == null || r ? N : N.contextElement || await (m.getDocumentElement == null ? void 0 : m.getDocumentElement(g.floating)),
    boundary: y,
    rootBoundary: S,
    strategy: p
  })), L = d === "floating" ? {
    x: c,
    y: f,
    width: v.floating.width,
    height: v.floating.height
  } : v.reference, J = await (m.getOffsetParent == null ? void 0 : m.getOffsetParent(g.floating)), K = await (m.isElement == null ? void 0 : m.isElement(J)) && await (m.getScale == null ? void 0 : m.getScale(J)) || {
    x: 1,
    y: 1
  }, I = Gr(m.convertOffsetParentRelativeRectToViewportRelativeRect ? await m.convertOffsetParentRelativeRectToViewportRelativeRect({
    elements: g,
    rect: L,
    offsetParent: J,
    strategy: p
  }) : L);
  return {
    top: (H.top - I.top + R.top) / K.y,
    bottom: (I.bottom - H.bottom + R.bottom) / K.y,
    left: (H.left - I.left + R.left) / K.x,
    right: (I.right - H.right + R.right) / K.x
  };
}
const NT = 50, DT = async (a, u, r) => {
  const {
    placement: c = "bottom",
    strategy: f = "absolute",
    middleware: m = [],
    platform: v
  } = r, g = v.detectOverflow ? v : {
    ...v,
    detectOverflow: RT
  }, p = await (v.isRTL == null ? void 0 : v.isRTL(u));
  let y = await v.getElementRects({
    reference: a,
    floating: u,
    strategy: f
  }), {
    x: S,
    y: d
  } = Y0(y, c, p), x = c, C = 0;
  const R = {};
  for (let O = 0; O < m.length; O++) {
    const N = m[O];
    if (!N)
      continue;
    const {
      name: H,
      fn: L
    } = N, {
      x: J,
      y: K,
      data: I,
      reset: Z
    } = await L({
      x: S,
      y: d,
      initialPlacement: c,
      placement: x,
      strategy: f,
      middlewareData: R,
      rects: y,
      platform: g,
      elements: {
        reference: a,
        floating: u
      }
    });
    S = J ?? S, d = K ?? d, R[H] = {
      ...R[H],
      ...I
    }, Z && C < NT && (C++, typeof Z == "object" && (Z.placement && (x = Z.placement), Z.rects && (y = Z.rects === !0 ? await v.getElementRects({
      reference: a,
      floating: u,
      strategy: f
    }) : Z.rects), {
      x: S,
      y: d
    } = Y0(y, x, p)), O = -1);
  }
  return {
    x: S,
    y: d,
    placement: x,
    strategy: f,
    middlewareData: R
  };
}, zT = (a) => ({
  name: "arrow",
  options: a,
  async fn(u) {
    const {
      x: r,
      y: c,
      placement: f,
      rects: m,
      platform: v,
      elements: g,
      middlewareData: p
    } = u, {
      element: y,
      padding: S = 0
    } = bl(a, u) || {};
    if (y == null)
      return {};
    const d = zp(S), x = {
      x: r,
      y: c
    }, C = zd(f), R = Dd(C), O = await v.getDimensions(y), N = C === "y", H = N ? "top" : "left", L = N ? "bottom" : "right", J = N ? "clientHeight" : "clientWidth", K = m.reference[R] + m.reference[C] - x[C] - m.floating[R], I = x[C] - m.reference[C], Z = await (v.getOffsetParent == null ? void 0 : v.getOffsetParent(y));
    let X = Z ? Z[J] : 0;
    (!X || !await (v.isElement == null ? void 0 : v.isElement(Z))) && (X = g.floating[J] || m.floating[R]);
    const Y = K / 2 - I / 2, dt = X / 2 - O[R] / 2 - 1, ht = Pl(d[H], dt), xt = Pl(d[L], dt), st = X - O[R] - xt, Tt = X / 2 - O[R] / 2 + Y, gt = Dp(ht, Tt, st), yt = !p.arrow && ji(f) != null && Tt !== gt && m.reference[R] / 2 - (Tt < ht ? ht : xt) - O[R] / 2 < 0, B = yt ? Tt < ht ? Tt - ht : Tt - st : 0;
    return {
      [C]: x[C] + B,
      data: {
        [C]: gt,
        centerOffset: Tt - gt - B,
        ...yt && {
          alignmentOffset: B
        }
      },
      reset: yt
    };
  }
}), MT = function(a) {
  return a === void 0 && (a = {}), {
    name: "flip",
    options: a,
    async fn(u) {
      var r, c;
      const {
        placement: f,
        middlewareData: m,
        rects: v,
        initialPlacement: g,
        platform: p,
        elements: y
      } = u, {
        mainAxis: S = !0,
        crossAxis: d = !0,
        fallbackPlacements: x,
        fallbackStrategy: C = "bestFit",
        fallbackAxisSideDirection: R = "none",
        flipAlignment: O = !0,
        ...N
      } = bl(a, u);
      if ((r = m.arrow) != null && r.alignmentOffset)
        return {};
      const H = Wl(f), L = Zn(g), J = Wl(g) === g, K = await (p.isRTL == null ? void 0 : p.isRTL(y.floating)), I = x || (J || !O ? [Vr(g)] : TT(g)), Z = R !== "none";
      !x && Z && I.push(..._T(g, O, R, K));
      const X = [g, ...I], Y = await p.detectOverflow(u, N), dt = [];
      let ht = ((c = m.flip) == null ? void 0 : c.overflows) || [];
      if (S && dt.push(Y[H]), d) {
        const gt = xT(f, v, K);
        dt.push(Y[gt[0]], Y[gt[1]]);
      }
      if (ht = [...ht, {
        placement: f,
        overflows: dt
      }], !dt.every((gt) => gt <= 0)) {
        var xt, st;
        const gt = (((xt = m.flip) == null ? void 0 : xt.index) || 0) + 1, yt = X[gt];
        if (yt && (!(d === "alignment" ? L !== Zn(yt) : !1) || // We leave the current main axis only if every placement on that axis
        // overflows the main axis.
        ht.every((P) => Zn(P.placement) === L ? P.overflows[0] > 0 : !0)))
          return {
            data: {
              index: gt,
              overflows: ht
            },
            reset: {
              placement: yt
            }
          };
        let B = (st = ht.filter((tt) => tt.overflows[0] <= 0).sort((tt, P) => tt.overflows[1] - P.overflows[1])[0]) == null ? void 0 : st.placement;
        if (!B)
          switch (C) {
            case "bestFit": {
              var Tt;
              const tt = (Tt = ht.filter((P) => {
                if (Z) {
                  const at = Zn(P.placement);
                  return at === L || // Create a bias to the `y` side axis due to horizontal
                  // reading directions favoring greater width.
                  at === "y";
                }
                return !0;
              }).map((P) => [P.placement, P.overflows.filter((at) => at > 0).reduce((at, F) => at + F, 0)]).sort((P, at) => P[1] - at[1])[0]) == null ? void 0 : Tt[0];
              tt && (B = tt);
              break;
            }
            case "initialPlacement":
              B = g;
              break;
          }
        if (f !== B)
          return {
            reset: {
              placement: B
            }
          };
      }
      return {};
    }
  };
};
function q0(a, u) {
  return {
    top: a.top - u.height,
    right: a.right - u.width,
    bottom: a.bottom - u.height,
    left: a.left - u.width
  };
}
function V0(a) {
  return ST.some((u) => a[u] >= 0);
}
const UT = function(a) {
  return a === void 0 && (a = {}), {
    name: "hide",
    options: a,
    async fn(u) {
      const {
        rects: r,
        platform: c
      } = u, {
        strategy: f = "referenceHidden",
        ...m
      } = bl(a, u);
      switch (f) {
        case "referenceHidden": {
          const v = await c.detectOverflow(u, {
            ...m,
            elementContext: "reference"
          }), g = q0(v, r.reference);
          return {
            data: {
              referenceHiddenOffsets: g,
              referenceHidden: V0(g)
            }
          };
        }
        case "escaped": {
          const v = await c.detectOverflow(u, {
            ...m,
            altBoundary: !0
          }), g = q0(v, r.floating);
          return {
            data: {
              escapedOffsets: g,
              escaped: V0(g)
            }
          };
        }
        default:
          return {};
      }
    }
  };
}, Mp = /* @__PURE__ */ new Set(["left", "top"]);
async function HT(a, u) {
  const {
    placement: r,
    platform: c,
    elements: f
  } = a, m = await (c.isRTL == null ? void 0 : c.isRTL(f.floating)), v = Wl(r), g = ji(r), p = Zn(r) === "y", y = Mp.has(v) ? -1 : 1, S = m && p ? -1 : 1, d = bl(u, a);
  let {
    mainAxis: x,
    crossAxis: C,
    alignmentAxis: R
  } = typeof d == "number" ? {
    mainAxis: d,
    crossAxis: 0,
    alignmentAxis: null
  } : {
    mainAxis: d.mainAxis || 0,
    crossAxis: d.crossAxis || 0,
    alignmentAxis: d.alignmentAxis
  };
  return g && typeof R == "number" && (C = g === "end" ? R * -1 : R), p ? {
    x: C * S,
    y: x * y
  } : {
    x: x * y,
    y: C * S
  };
}
const jT = function(a) {
  return a === void 0 && (a = 0), {
    name: "offset",
    options: a,
    async fn(u) {
      var r, c;
      const {
        x: f,
        y: m,
        placement: v,
        middlewareData: g
      } = u, p = await HT(u, a);
      return v === ((r = g.offset) == null ? void 0 : r.placement) && (c = g.arrow) != null && c.alignmentOffset ? {} : {
        x: f + p.x,
        y: m + p.y,
        data: {
          ...p,
          placement: v
        }
      };
    }
  };
}, BT = function(a) {
  return a === void 0 && (a = {}), {
    name: "shift",
    options: a,
    async fn(u) {
      const {
        x: r,
        y: c,
        placement: f,
        platform: m
      } = u, {
        mainAxis: v = !0,
        crossAxis: g = !1,
        limiter: p = {
          fn: (L) => {
            let {
              x: J,
              y: K
            } = L;
            return {
              x: J,
              y: K
            };
          }
        },
        ...y
      } = bl(a, u), S = {
        x: r,
        y: c
      }, d = await m.detectOverflow(u, y), x = Zn(f), C = Nd(x);
      let R = S[C], O = S[x];
      const N = (L, J) => Dp(J + d[L === "y" ? "top" : "left"], J, J - d[L === "y" ? "bottom" : "right"]);
      v && (R = N(C, R)), g && (O = N(x, O));
      const H = p.fn({
        ...u,
        [C]: R,
        [x]: O
      });
      return {
        ...H,
        data: {
          x: H.x - r,
          y: H.y - c,
          enabled: {
            [C]: v,
            [x]: g
          }
        }
      };
    }
  };
}, LT = function(a) {
  return a === void 0 && (a = {}), {
    options: a,
    fn(u) {
      var r, c;
      const {
        x: f,
        y: m,
        placement: v,
        rects: g,
        middlewareData: p
      } = u, {
        offset: y = 0,
        mainAxis: S = !0,
        crossAxis: d = !0
      } = bl(a, u), x = {
        x: f,
        y: m
      }, C = Zn(v), R = Nd(C);
      let O = x[R], N = x[C];
      const H = bl(y, u), L = typeof H == "number" ? {
        mainAxis: H,
        crossAxis: 0
      } : {
        mainAxis: (r = H.mainAxis) != null ? r : 0,
        crossAxis: (c = H.crossAxis) != null ? c : 0
      };
      if (S) {
        const I = R === "y" ? "height" : "width", Z = g.reference[R] - g.floating[I] + L.mainAxis, X = g.reference[R] + g.reference[I] - L.mainAxis;
        O < Z ? O = Z : O > X && (O = X);
      }
      if (d) {
        var J, K;
        const I = R === "y" ? "width" : "height", Z = Mp.has(Wl(v)), X = g.reference[C] - g.floating[I] + (Z && ((J = p.offset) == null ? void 0 : J[C]) || 0) + (Z ? 0 : L.crossAxis), Y = g.reference[C] + g.reference[I] + (Z ? 0 : ((K = p.offset) == null ? void 0 : K[C]) || 0) - (Z ? L.crossAxis : 0);
        N < X ? N = X : N > Y && (N = Y);
      }
      return {
        [R]: O,
        [C]: N
      };
    }
  };
}, YT = function(a) {
  return a === void 0 && (a = {}), {
    name: "size",
    options: a,
    async fn(u) {
      const {
        placement: r,
        rects: c,
        platform: f,
        elements: m
      } = u, {
        apply: v = () => {
        },
        ...g
      } = bl(a, u), p = await f.detectOverflow(u, g), y = Wl(r), S = ji(r), d = Zn(r) === "y", {
        width: x,
        height: C
      } = c.floating;
      let R, O;
      y === "top" || y === "bottom" ? (R = y, O = S === (await (f.isRTL == null ? void 0 : f.isRTL(m.floating)) ? "start" : "end") ? "left" : "right") : (O = y, R = S === "end" ? "top" : "bottom");
      const N = C - p.top - p.bottom, H = x - p.left - p.right, L = Pl(C - p[R], N), J = Pl(x - p[O], H), K = u.middlewareData.shift, I = !K;
      let Z = L, X = J;
      K != null && K.enabled.x && (X = H), K != null && K.enabled.y && (Z = N), I && !S && (d ? X = x - 2 * gl(p.left, p.right) : Z = C - 2 * gl(p.top, p.bottom)), await v({
        ...u,
        availableWidth: X,
        availableHeight: Z
      });
      const Y = await f.getDimensions(m.floating);
      return x !== Y.width || C !== Y.height ? {
        reset: {
          rects: !0
        }
      } : {};
    }
  };
};
function Fr() {
  return typeof window < "u";
}
function Bi(a) {
  return Up(a) ? (a.nodeName || "").toLowerCase() : "#document";
}
function Qe(a) {
  var u;
  return (a == null || (u = a.ownerDocument) == null ? void 0 : u.defaultView) || window;
}
function Sl(a) {
  var u;
  return (u = (Up(a) ? a.ownerDocument : a.document) || window.document) == null ? void 0 : u.documentElement;
}
function Up(a) {
  return Fr() ? a instanceof Node || a instanceof Qe(a).Node : !1;
}
function Kn(a) {
  return Fr() ? a instanceof Element || a instanceof Qe(a).Element : !1;
}
function ea(a) {
  return Fr() ? a instanceof HTMLElement || a instanceof Qe(a).HTMLElement : !1;
}
function G0(a) {
  return !Fr() || typeof ShadowRoot > "u" ? !1 : a instanceof ShadowRoot || a instanceof Qe(a).ShadowRoot;
}
function $r(a) {
  const {
    overflow: u,
    overflowX: r,
    overflowY: c,
    display: f
  } = Jn(a);
  return /auto|scroll|overlay|hidden|clip/.test(u + c + r) && f !== "inline" && f !== "contents";
}
function qT(a) {
  return /^(table|td|th)$/.test(Bi(a));
}
function Ir(a) {
  try {
    if (a.matches(":popover-open"))
      return !0;
  } catch {
  }
  try {
    return a.matches(":modal");
  } catch {
    return !1;
  }
}
const VT = /transform|translate|scale|rotate|perspective|filter/, GT = /paint|layout|strict|content/, Aa = (a) => !!a && a !== "none";
let Qf;
function Md(a) {
  const u = Kn(a) ? Jn(a) : a;
  return Aa(u.transform) || Aa(u.translate) || Aa(u.scale) || Aa(u.rotate) || Aa(u.perspective) || !Ud() && (Aa(u.backdropFilter) || Aa(u.filter)) || VT.test(u.willChange || "") || GT.test(u.contain || "");
}
function XT(a) {
  let u = za(a);
  for (; ea(u) && !ko(u); ) {
    if (Md(u))
      return u;
    if (Ir(u))
      return null;
    u = za(u);
  }
  return null;
}
function Ud() {
  return Qf == null && (Qf = typeof CSS < "u" && CSS.supports && CSS.supports("-webkit-backdrop-filter", "none")), Qf;
}
function ko(a) {
  return /^(html|body|#document)$/.test(Bi(a));
}
function Jn(a) {
  return Qe(a).getComputedStyle(a);
}
function Pr(a) {
  return Kn(a) ? {
    scrollLeft: a.scrollLeft,
    scrollTop: a.scrollTop
  } : {
    scrollLeft: a.scrollX,
    scrollTop: a.scrollY
  };
}
function za(a) {
  if (Bi(a) === "html")
    return a;
  const u = (
    // Step into the shadow DOM of the parent of a slotted node.
    a.assignedSlot || // DOM Element detected.
    a.parentNode || // ShadowRoot detected.
    G0(a) && a.host || // Fallback.
    Sl(a)
  );
  return G0(u) ? u.host : u;
}
function Hp(a) {
  const u = za(a);
  return ko(u) ? (a.ownerDocument || a).body : ea(u) && $r(u) ? u : Hp(u);
}
function Qo(a, u, r) {
  var c;
  u === void 0 && (u = []), r === void 0 && (r = !0);
  const f = Hp(a), m = f === ((c = a.ownerDocument) == null ? void 0 : c.body), v = Qe(f);
  if (m) {
    const g = cd(v);
    return u.concat(v, v.visualViewport || [], $r(f) ? f : [], g && r ? Qo(g) : []);
  } else
    return u.concat(f, Qo(f, [], r));
}
function cd(a) {
  return a.parent && Object.getPrototypeOf(a.parent) ? a.frameElement : null;
}
function jp(a) {
  const u = Jn(a);
  let r = parseFloat(u.width) || 0, c = parseFloat(u.height) || 0;
  const f = ea(a), m = f ? a.offsetWidth : r, v = f ? a.offsetHeight : c, g = qr(r) !== m || qr(c) !== v;
  return g && (r = m, c = v), {
    width: r,
    height: c,
    $: g
  };
}
function Hd(a) {
  return Kn(a) ? a : a.contextElement;
}
function Ui(a) {
  const u = Hd(a);
  if (!ea(u))
    return yl(1);
  const r = u.getBoundingClientRect(), {
    width: c,
    height: f,
    $: m
  } = jp(u);
  let v = (m ? qr(r.width) : r.width) / c, g = (m ? qr(r.height) : r.height) / f;
  return (!v || !Number.isFinite(v)) && (v = 1), (!g || !Number.isFinite(g)) && (g = 1), {
    x: v,
    y: g
  };
}
const kT = /* @__PURE__ */ yl(0);
function Bp(a) {
  const u = Qe(a);
  return !Ud() || !u.visualViewport ? kT : {
    x: u.visualViewport.offsetLeft,
    y: u.visualViewport.offsetTop
  };
}
function QT(a, u, r) {
  return u === void 0 && (u = !1), !!r && u && r === Qe(a);
}
function Ma(a, u, r, c) {
  u === void 0 && (u = !1), r === void 0 && (r = !1);
  const f = a.getBoundingClientRect(), m = Hd(a);
  let v = yl(1);
  u && (c ? Kn(c) && (v = Ui(c)) : v = Ui(a));
  const g = QT(m, r, c) ? Bp(m) : yl(0);
  let p = (f.left + g.x) / v.x, y = (f.top + g.y) / v.y, S = f.width / v.x, d = f.height / v.y;
  if (m && c) {
    const x = Qe(m), C = Kn(c) ? Qe(c) : c;
    let R = x, O = cd(R);
    for (; O && C !== R; ) {
      const N = Ui(O), H = O.getBoundingClientRect(), L = Jn(O), J = H.left + (O.clientLeft + parseFloat(L.paddingLeft)) * N.x, K = H.top + (O.clientTop + parseFloat(L.paddingTop)) * N.y;
      p *= N.x, y *= N.y, S *= N.x, d *= N.y, p += J, y += K, R = Qe(O), O = cd(R);
    }
  }
  return Gr({
    width: S,
    height: d,
    x: p,
    y
  });
}
function Wr(a, u) {
  const r = Pr(a).scrollLeft;
  return u ? u.left + r : Ma(Sl(a)).left + r;
}
function Lp(a, u) {
  const r = a.getBoundingClientRect(), c = r.left + u.scrollLeft - Wr(a, r), f = r.top + u.scrollTop;
  return {
    x: c,
    y: f
  };
}
function ZT(a) {
  let {
    elements: u,
    rect: r,
    offsetParent: c,
    strategy: f
  } = a;
  const m = f === "fixed", v = Sl(c), g = u ? Ir(u.floating) : !1;
  if (c === v || g && m)
    return r;
  let p = {
    scrollLeft: 0,
    scrollTop: 0
  }, y = yl(1);
  const S = yl(0), d = ea(c);
  if ((d || !m) && ((Bi(c) !== "body" || $r(v)) && (p = Pr(c)), d)) {
    const C = Ma(c);
    y = Ui(c), S.x = C.x + c.clientLeft, S.y = C.y + c.clientTop;
  }
  const x = v && !d && !m ? Lp(v, p) : yl(0);
  return {
    width: r.width * y.x,
    height: r.height * y.y,
    x: r.x * y.x - p.scrollLeft * y.x + S.x + x.x,
    y: r.y * y.y - p.scrollTop * y.y + S.y + x.y
  };
}
function KT(a) {
  return a.getClientRects ? Array.from(a.getClientRects()) : [];
}
function JT(a) {
  const u = Pr(a), r = a.ownerDocument.body, c = gl(a.scrollWidth, a.clientWidth, r.scrollWidth, r.clientWidth), f = gl(a.scrollHeight, a.clientHeight, r.scrollHeight, r.clientHeight);
  let m = -u.scrollLeft + Wr(a);
  const v = -u.scrollTop;
  return Jn(r).direction === "rtl" && (m += gl(a.clientWidth, r.clientWidth) - c), {
    width: c,
    height: f,
    x: m,
    y: v
  };
}
const FT = 25;
function $T(a, u, r) {
  r === void 0 && (r = "viewport");
  const c = r === "layoutViewport", f = Qe(a), m = Sl(a), v = f.visualViewport;
  let g = m.clientWidth, p = m.clientHeight, y = 0, S = 0;
  if (v) {
    const x = !Ud() || u === "fixed";
    c ? x || (y = -v.offsetLeft, S = -v.offsetTop) : (g = v.width, p = v.height, x && (y = v.offsetLeft, S = v.offsetTop));
  }
  if (Wr(m) <= 0) {
    const x = m.ownerDocument, C = x.body, R = getComputedStyle(C), O = x.compatMode === "CSS1Compat" && parseFloat(R.marginLeft) + parseFloat(R.marginRight) || 0, N = Math.abs(m.clientWidth - C.clientWidth - O), H = getComputedStyle(m).scrollbarGutter === "stable both-edges" ? N / 2 : N;
    H <= FT && (g -= H);
  }
  return {
    width: g,
    height: p,
    x: y,
    y: S
  };
}
function IT(a, u) {
  const r = Ma(a, !0, u === "fixed"), c = r.top + a.clientTop, f = r.left + a.clientLeft, m = Ui(a), v = a.clientWidth * m.x, g = a.clientHeight * m.y, p = f * m.x, y = c * m.y;
  return {
    width: v,
    height: g,
    x: p,
    y
  };
}
function X0(a, u, r) {
  let c;
  if (u === "viewport" || u === "layoutViewport")
    c = $T(a, r, u);
  else if (u === "document")
    c = JT(Sl(a));
  else if (Kn(u))
    c = IT(u, r);
  else {
    const f = Bp(a);
    c = {
      x: u.x - f.x,
      y: u.y - f.y,
      width: u.width,
      height: u.height
    };
  }
  return Gr(c);
}
function PT(a, u) {
  const r = u.get(a);
  if (r)
    return r;
  let c = Qo(a, [], !1).filter((g) => Kn(g) && Bi(g) !== "body"), f = null;
  const m = Jn(a).position === "fixed";
  let v = m ? za(a) : a;
  for (; Kn(v) && !ko(v); ) {
    const g = Jn(v), p = Md(v), y = f ? f.position : m ? "fixed" : "";
    !p && (y === "fixed" || y === "absolute" && g.position === "static") ? c = c.filter((d) => d !== v) : f = g, v = za(v);
  }
  return u.set(a, c), c;
}
function WT(a) {
  let {
    element: u,
    boundary: r,
    rootBoundary: c,
    strategy: f
  } = a;
  const v = [...r === "clippingAncestors" ? Ir(u) ? [] : PT(u, this._c) : [].concat(r), c], g = X0(u, v[0], f);
  let p = g.top, y = g.right, S = g.bottom, d = g.left;
  for (let x = 1; x < v.length; x++) {
    const C = X0(u, v[x], f);
    p = gl(C.top, p), y = Pl(C.right, y), S = Pl(C.bottom, S), d = gl(C.left, d);
  }
  return {
    width: y - d,
    height: S - p,
    x: d,
    y: p
  };
}
function tw(a) {
  const {
    width: u,
    height: r
  } = jp(a);
  return {
    width: u,
    height: r
  };
}
function ew(a, u, r) {
  const c = ea(u), f = Sl(u), m = r === "fixed", v = Ma(a, !0, m, u);
  let g = {
    scrollLeft: 0,
    scrollTop: 0
  };
  const p = yl(0);
  if ((c || !m) && ((Bi(u) !== "body" || $r(f)) && (g = Pr(u)), c)) {
    const x = Ma(u, !0, m, u);
    p.x = x.x + u.clientLeft, p.y = x.y + u.clientTop;
  }
  !c && f && (p.x = Wr(f));
  const y = f && !c && !m ? Lp(f, g) : yl(0), S = v.left + g.scrollLeft - p.x - y.x, d = v.top + g.scrollTop - p.y - y.y;
  return {
    x: S,
    y: d,
    width: v.width,
    height: v.height
  };
}
function Zf(a) {
  return Jn(a).position === "static";
}
function k0(a, u) {
  if (!ea(a) || Jn(a).position === "fixed")
    return null;
  if (u)
    return u(a);
  let r = a.offsetParent;
  return Sl(a) === r && (r = r.ownerDocument.body), r;
}
function Yp(a, u) {
  const r = Qe(a);
  if (Ir(a))
    return r;
  if (!ea(a)) {
    let f = za(a);
    for (; f && !ko(f); ) {
      if (Kn(f) && !Zf(f))
        return f;
      f = za(f);
    }
    return r;
  }
  let c = k0(a, u);
  for (; c && qT(c) && Zf(c); )
    c = k0(c, u);
  return c && ko(c) && Zf(c) && !Md(c) ? r : c || XT(a) || r;
}
const nw = async function(a) {
  const u = this.getOffsetParent || Yp, r = this.getDimensions, c = await r(a.floating);
  return {
    reference: ew(a.reference, await u(a.floating), a.strategy),
    floating: {
      x: 0,
      y: 0,
      width: c.width,
      height: c.height
    }
  };
};
function lw(a) {
  return Jn(a).direction === "rtl";
}
const aw = {
  convertOffsetParentRelativeRectToViewportRelativeRect: ZT,
  getDocumentElement: Sl,
  getClippingRect: WT,
  getOffsetParent: Yp,
  getElementRects: nw,
  getClientRects: KT,
  getDimensions: tw,
  getScale: Ui,
  isElement: Kn,
  isRTL: lw
};
function qp(a, u) {
  return a.x === u.x && a.y === u.y && a.width === u.width && a.height === u.height;
}
function iw(a, u, r) {
  let c = null, f;
  const m = Sl(a);
  function v() {
    var S;
    clearTimeout(f), (S = c) == null || S.disconnect(), c = null;
  }
  function g(S, d) {
    S === void 0 && (S = !1), d === void 0 && (d = 1), v();
    const x = a.getBoundingClientRect(), {
      left: C,
      top: R,
      width: O,
      height: N
    } = x;
    if (S || u(), !O || !N)
      return;
    const H = Ur(R), L = Ur(m.clientWidth - (C + O)), J = Ur(m.clientHeight - (R + N)), K = Ur(C), Z = {
      rootMargin: -H + "px " + -L + "px " + -J + "px " + -K + "px",
      threshold: gl(0, Pl(1, d)) || 1
    };
    let X = !0;
    function Y(dt) {
      const ht = dt[0].intersectionRatio;
      if (!qp(x, a.getBoundingClientRect()))
        return g();
      if (ht !== d) {
        if (!X)
          return g();
        ht ? g(!1, ht) : f = setTimeout(() => {
          g(!1, 1e-7);
        }, 1e3);
      }
      X = !1;
    }
    try {
      c = new IntersectionObserver(Y, {
        ...Z,
        // Handle <iframe>s
        root: m.ownerDocument
      });
    } catch {
      c = new IntersectionObserver(Y, Z);
    }
    c.observe(a);
  }
  const p = Qe(a), y = () => g(r);
  return p.addEventListener("resize", y), g(!0), () => {
    p.removeEventListener("resize", y), v();
  };
}
function ow(a, u, r, c) {
  c === void 0 && (c = {});
  const {
    ancestorScroll: f = !0,
    ancestorResize: m = !0,
    elementResize: v = typeof ResizeObserver == "function",
    layoutShift: g = typeof IntersectionObserver == "function",
    animationFrame: p = !1
  } = c, y = Hd(a), S = f || m ? [...y ? Qo(y) : [], ...u ? Qo(u) : []] : [];
  S.forEach((H) => {
    f && H.addEventListener("scroll", r), m && H.addEventListener("resize", r);
  });
  const d = y && g ? iw(y, r, m) : null;
  let x = -1, C = null;
  v && (C = new ResizeObserver((H) => {
    let [L] = H;
    L && L.target === y && C && u && (C.unobserve(u), cancelAnimationFrame(x), x = requestAnimationFrame(() => {
      var J;
      (J = C) == null || J.observe(u);
    })), r();
  }), y && !p && C.observe(y), u && C.observe(u));
  let R, O = p ? Ma(a) : null;
  p && N();
  function N() {
    const H = Ma(a);
    O && !qp(O, H) && r(), O = H, R = requestAnimationFrame(N);
  }
  return r(), () => {
    var H;
    S.forEach((L) => {
      f && L.removeEventListener("scroll", r), m && L.removeEventListener("resize", r);
    }), d == null || d(), (H = C) == null || H.disconnect(), C = null, p && cancelAnimationFrame(R);
  };
}
const uw = jT, rw = BT, cw = MT, sw = YT, fw = UT, Q0 = zT, dw = LT, mw = (a, u, r) => {
  const c = /* @__PURE__ */ new Map(), f = r ?? {}, m = {
    ...aw,
    ...f.platform,
    _c: c
  };
  return DT(a, u, {
    ...f,
    platform: m
  });
};
var vw = typeof document < "u", hw = function() {
}, Lr = vw ? b.useLayoutEffect : hw;
function Xr(a, u) {
  if (a === u)
    return !0;
  if (typeof a != typeof u)
    return !1;
  if (typeof a == "function" && a.toString() === u.toString())
    return !0;
  let r, c, f;
  if (a && u && typeof a == "object") {
    if (Array.isArray(a)) {
      if (r = a.length, r !== u.length) return !1;
      for (c = r; c-- !== 0; )
        if (!Xr(a[c], u[c]))
          return !1;
      return !0;
    }
    if (f = Object.keys(a), r = f.length, r !== Object.keys(u).length)
      return !1;
    for (c = r; c-- !== 0; )
      if (!{}.hasOwnProperty.call(u, f[c]))
        return !1;
    for (c = r; c-- !== 0; ) {
      const m = f[c];
      if (!(m === "_owner" && a.$$typeof) && !Xr(a[m], u[m]))
        return !1;
    }
    return !0;
  }
  return a !== a && u !== u;
}
function Vp(a) {
  return typeof window > "u" ? 1 : (a.ownerDocument.defaultView || window).devicePixelRatio || 1;
}
function Z0(a, u) {
  const r = Vp(a);
  return Math.round(u * r) / r;
}
function Kf(a) {
  const u = b.useRef(a);
  return Lr(() => {
    u.current = a;
  }), u;
}
function gw(a) {
  a === void 0 && (a = {});
  const {
    placement: u = "bottom",
    strategy: r = "absolute",
    middleware: c = [],
    platform: f,
    elements: {
      reference: m,
      floating: v
    } = {},
    transform: g = !0,
    whileElementsMounted: p,
    open: y
  } = a, [S, d] = b.useState({
    x: 0,
    y: 0,
    strategy: r,
    placement: u,
    middlewareData: {},
    isPositioned: !1
  }), [x, C] = b.useState(c);
  Xr(x, c) || C(c);
  const [R, O] = b.useState(null), [N, H] = b.useState(null), L = b.useCallback((P) => {
    P !== Z.current && (Z.current = P, O(P));
  }, []), J = b.useCallback((P) => {
    P !== X.current && (X.current = P, H(P));
  }, []), K = m || R, I = v || N, Z = b.useRef(null), X = b.useRef(null), Y = b.useRef(S), dt = p != null, ht = Kf(p), xt = Kf(f), st = Kf(y), Tt = b.useCallback(() => {
    if (!Z.current || !X.current)
      return;
    const P = {
      placement: u,
      strategy: r,
      middleware: x
    };
    xt.current && (P.platform = xt.current), mw(Z.current, X.current, P).then((at) => {
      const F = {
        ...at,
        // The floating element's position may be recomputed while it's closed
        // but still mounted (such as when transitioning out). To ensure
        // `isPositioned` will be `false` initially on the next open, avoid
        // setting it to `true` when `open === false` (must be specified).
        isPositioned: st.current !== !1
      };
      gt.current && !Xr(Y.current, F) && (Y.current = F, Zr.flushSync(() => {
        d(F);
      }));
    });
  }, [x, u, r, xt, st]);
  Lr(() => {
    y === !1 && Y.current.isPositioned && (Y.current.isPositioned = !1, d((P) => ({
      ...P,
      isPositioned: !1
    })));
  }, [y]);
  const gt = b.useRef(!1);
  Lr(() => (gt.current = !0, () => {
    gt.current = !1;
  }), []), Lr(() => {
    if (K && (Z.current = K), I && (X.current = I), K && I) {
      if (ht.current)
        return ht.current(K, I, Tt);
      Tt();
    }
  }, [K, I, Tt, ht, dt]);
  const yt = b.useMemo(() => ({
    reference: Z,
    floating: X,
    setReference: L,
    setFloating: J
  }), [L, J]), B = b.useMemo(() => ({
    reference: K,
    floating: I
  }), [K, I]), tt = b.useMemo(() => {
    const P = {
      position: r,
      left: 0,
      top: 0
    };
    if (!B.floating)
      return P;
    const at = Z0(B.floating, S.x), F = Z0(B.floating, S.y);
    return g ? {
      ...P,
      transform: "translate(" + at + "px, " + F + "px)",
      ...Vp(B.floating) >= 1.5 && {
        willChange: "transform"
      }
    } : {
      position: r,
      left: at,
      top: F
    };
  }, [r, g, B.floating, S.x, S.y]);
  return b.useMemo(() => ({
    ...S,
    update: Tt,
    refs: yt,
    elements: B,
    floatingStyles: tt
  }), [S, Tt, yt, B, tt]);
}
const yw = (a) => {
  function u(r) {
    return {}.hasOwnProperty.call(r, "current");
  }
  return {
    name: "arrow",
    options: a,
    fn(r) {
      const {
        element: c,
        padding: f
      } = typeof a == "function" ? a(r) : a;
      return c && u(c) ? c.current != null ? Q0({
        element: c.current,
        padding: f
      }).fn(r) : {} : c ? Q0({
        element: c,
        padding: f
      }).fn(r) : {};
    }
  };
}, pw = (a, u) => {
  const r = uw(a);
  return {
    name: r.name,
    fn: r.fn,
    options: [a, u]
  };
}, bw = (a, u) => {
  const r = rw(a);
  return {
    name: r.name,
    fn: r.fn,
    options: [a, u]
  };
}, Sw = (a, u) => ({
  fn: dw(a).fn,
  options: [a, u]
}), Ew = (a, u) => {
  const r = cw(a);
  return {
    name: r.name,
    fn: r.fn,
    options: [a, u]
  };
}, xw = (a, u) => {
  const r = sw(a);
  return {
    name: r.name,
    fn: r.fn,
    options: [a, u]
  };
}, Tw = (a, u) => {
  const r = fw(a);
  return {
    name: r.name,
    fn: r.fn,
    options: [a, u]
  };
}, ww = (a, u) => {
  const r = yw(a);
  return {
    name: r.name,
    fn: r.fn,
    options: [a, u]
  };
};
var Cw = Object.defineProperty, Ow = (a, u) => Cw(a, "name", { value: u, configurable: !0 });
function Gp(a) {
  const [u, r] = b.useState(void 0);
  return ln(() => {
    if (a) {
      r({ width: a.offsetWidth, height: a.offsetHeight });
      const c = new ResizeObserver((f) => {
        if (!Array.isArray(f) || !f.length)
          return;
        const m = f[0];
        let v, g;
        if ("borderBoxSize" in m) {
          const p = m.borderBoxSize, y = Array.isArray(p) ? p[0] : p;
          v = y.inlineSize, g = y.blockSize;
        } else
          v = a.offsetWidth, g = a.offsetHeight;
        r({ width: v, height: g });
      });
      return c.observe(a, { box: "border-box" }), () => c.unobserve(a);
    } else
      r(void 0);
  }, [a]), u;
}
Ow(Gp, "useSize");
var _w = Object.defineProperty, $l = (a, u) => _w(a, "name", { value: u, configurable: !0 }), Xp = "Popper", [kp, Qp] = /* @__PURE__ */ Qr(Xp), [Aw, Zp] = kp(Xp), Rw = /* @__PURE__ */ $l((a) => {
  const { __scopePopper: u, children: r } = a, [c, f] = b.useState(null), [m, v] = b.useState(void 0);
  return /* @__PURE__ */ k.jsx(
    Aw,
    {
      scope: u,
      anchor: c,
      onAnchorChange: f,
      placementState: m,
      setPlacementState: v,
      children: r
    }
  );
}, "Popper"), Nw = "PopperAnchor", Dw = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ $l(function(u, r) {
    const { __scopePopper: c, virtualRef: f, ...m } = u, v = Zp(Nw, c), g = b.useRef(null), p = v.onAnchorChange, y = b.useCallback(
      (O) => {
        g.current = O, O && p(O);
      },
      [p]
    ), S = Fn(r, y), d = b.useRef(null);
    b.useEffect(() => {
      if (!f)
        return;
      const O = d.current;
      d.current = f.current, O !== d.current && p(d.current);
    });
    const x = v.placementState && tc(v.placementState), C = x == null ? void 0 : x[0], R = x == null ? void 0 : x[1];
    return f ? null : /* @__PURE__ */ k.jsx(
      se.div,
      {
        "data-radix-popper-side": C,
        "data-radix-popper-align": R,
        ...m,
        ref: S
      }
    );
  }, "PopperAnchor")
), Kp = "PopperContent", [zw, kC] = kp(Kp), Mw = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ $l(function(u, r) {
    var W, bt, lt, mt, It, _e, bn;
    const {
      __scopePopper: c,
      side: f = "bottom",
      sideOffset: m = 0,
      align: v = "center",
      alignOffset: g = 0,
      arrowPadding: p = 0,
      avoidCollisions: y = !0,
      collisionBoundary: S = [],
      collisionPadding: d = 0,
      sticky: x = "partial",
      hideWhenDetached: C = !1,
      updatePositionStrategy: R = "optimized",
      onPlaced: O,
      ...N
    } = u, H = Zp(Kp, c), [L, J] = b.useState(null), K = Fn(r, J), [I, Z] = b.useState(null), X = Gp(I), Y = (X == null ? void 0 : X.width) ?? 0, dt = (X == null ? void 0 : X.height) ?? 0, ht = f + (v !== "center" ? "-" + v : ""), xt = typeof d == "number" ? d : { top: 0, right: 0, bottom: 0, left: 0, ...d }, st = Array.isArray(S) ? S : [S], Tt = st.length > 0, gt = {
      padding: xt,
      boundary: st.filter(Jp),
      // with `strategy: 'fixed'`, this is the only way to get it to respect boundaries
      altBoundary: Tt
    }, { refs: yt, floatingStyles: B, placement: tt, isPositioned: P, middlewareData: at } = gw({
      // default to `fixed` strategy so users don't have to pick and we also avoid focus scroll issues
      strategy: "fixed",
      placement: ht,
      whileElementsMounted: /* @__PURE__ */ $l((...ye) => ow(...ye, {
        animationFrame: R === "always"
      }), "whileElementsMounted"),
      elements: {
        reference: H.anchor
      },
      middleware: [
        pw({ mainAxis: m + dt, alignmentAxis: g }),
        y && bw({
          mainAxis: !0,
          crossAxis: !1,
          limiter: x === "partial" ? Sw() : void 0,
          ...gt
        }),
        y && Ew({ ...gt }),
        xw({
          ...gt,
          apply: /* @__PURE__ */ $l(({ elements: ye, rects: Qt, availableWidth: Ut, availableHeight: Pt }) => {
            const { width: In, height: an } = Qt.reference, Jt = ye.floating.style;
            Jt.setProperty("--radix-popper-available-width", `${Ut}px`), Jt.setProperty("--radix-popper-available-height", `${Pt}px`), Jt.setProperty("--radix-popper-anchor-width", `${In}px`), Jt.setProperty("--radix-popper-anchor-height", `${an}px`);
          }, "apply")
        }),
        I && ww({ element: I, padding: p }),
        Uw({ arrowWidth: Y, arrowHeight: dt }),
        C && Tw({
          strategy: "referenceHidden",
          ...gt,
          // `hide` detects whether the anchor (reference) is clipped, so when
          // no explicit `collisionBoundary` is set we fall back to Floating
          // UI's default clipping ancestors (e.g. a scrollable menu). This
          // lets an occluded submenu hide once its anchor scrolls out of view
          // (#3237). The collision/size middlewares deliberately keep the
          // viewport-based default to avoid clamping content rendered inside
          // transformed or overflow-clipping portal containers.
          boundary: Tt ? gt.boundary : void 0
        })
      ]
    }), F = H.setPlacementState;
    ln(() => (F(tt), () => {
      F(void 0);
    }), [tt, F]);
    const [Bt, Q] = tc(tt), rt = Na(O);
    ln(() => {
      P && (rt == null || rt());
    }, [P, rt]);
    const E = (W = at.arrow) == null ? void 0 : W.x, _ = (bt = at.arrow) == null ? void 0 : bt.y, V = ((lt = at.arrow) == null ? void 0 : lt.centerOffset) !== 0, [$, ft] = b.useState();
    return ln(() => {
      L && ft(window.getComputedStyle(L).zIndex);
    }, [L]), /* @__PURE__ */ k.jsx(
      "div",
      {
        ref: yt.setFloating,
        "data-radix-popper-content-wrapper": "",
        style: {
          ...B,
          transform: P ? B.transform : "translate(0, -200%)",
          // keep off the page when measuring
          minWidth: "max-content",
          zIndex: $,
          "--radix-popper-transform-origin": [
            (mt = at.transformOrigin) == null ? void 0 : mt.x,
            (It = at.transformOrigin) == null ? void 0 : It.y
          ].join(" "),
          // hide the content if using the hide middleware and should be hidden
          // set visibility to hidden and disable pointer events so the UI behaves
          // as if the PopperContent isn't there at all
          ...((_e = at.hide) == null ? void 0 : _e.referenceHidden) && {
            visibility: "hidden",
            pointerEvents: "none"
          }
        },
        dir: u.dir,
        children: /* @__PURE__ */ k.jsx(
          zw,
          {
            scope: c,
            placedSide: Bt,
            placedAlign: Q,
            onArrowChange: Z,
            arrowX: E,
            arrowY: _,
            shouldHideArrow: V,
            children: /* @__PURE__ */ k.jsx(
              se.div,
              {
                "data-side": Bt,
                "data-align": Q,
                ...N,
                ref: K,
                style: {
                  ...N.style,
                  // if the PopperContent hasn't been placed yet (not all
                  // measurements done) we prevent animations so that users'
                  // animations don't kick in too early from the wrong sides.
                  animation: P ? (bn = N.style) == null ? void 0 : bn.animation : "none"
                }
              }
            )
          }
        )
      }
    );
  }, "PopperContent")
);
function Jp(a) {
  return a !== null;
}
$l(Jp, "isNotNull");
var Uw = /* @__PURE__ */ $l((a) => ({
  name: "transformOrigin",
  options: a,
  fn(u) {
    var N, H, L;
    const { placement: r, rects: c, middlewareData: f } = u, v = ((N = f.arrow) == null ? void 0 : N.centerOffset) !== 0, g = v ? 0 : a.arrowWidth, p = v ? 0 : a.arrowHeight, [y, S] = tc(r), d = { start: "0%", center: "50%", end: "100%" }[S], x = (((H = f.arrow) == null ? void 0 : H.x) ?? 0) + g / 2, C = (((L = f.arrow) == null ? void 0 : L.y) ?? 0) + p / 2;
    let R = "", O = "";
    return y === "bottom" ? (R = v ? d : `${x}px`, O = `${-p}px`) : y === "top" ? (R = v ? d : `${x}px`, O = `${c.floating.height + p}px`) : y === "right" ? (R = `${-p}px`, O = v ? d : `${C}px`) : y === "left" && (R = `${c.floating.width + p}px`, O = v ? d : `${C}px`), { data: { x: R, y: O } };
  }
}), "transformOrigin");
function tc(a) {
  const [u, r = "center"] = a.split("-");
  return [u, r];
}
$l(tc, "getSideAndAlignFromPlacement");
var Hw = Rw, jw = Dw, Bw = Mw, Lw = Object.defineProperty, Yw = (a, u) => Lw(a, "name", { value: u, configurable: !0 }), qw = Object.freeze({
  // See: https://github.com/twbs/bootstrap/blob/main/scss/mixins/_visually-hidden.scss
  position: "absolute",
  border: 0,
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  wordWrap: "normal"
}), Vw = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ Yw(function(u, r) {
    return /* @__PURE__ */ k.jsx(
      se.span,
      {
        ...u,
        ref: r,
        style: { ...qw, ...u.style }
      }
    );
  }, "VisuallyHidden")
), Gw = Vw, Xw = Object.defineProperty, ge = (a, u) => Xw(a, "name", { value: u, configurable: !0 }), [jd, QC] = /* @__PURE__ */ Qr("Tooltip", [
  Qp
]), Bd = Qp(), kw = "TooltipProvider", Qw = 700, sd = "tooltip.open", [Zw, Ld] = jd(kw), Kw = /* @__PURE__ */ ge((a) => {
  const {
    __scopeTooltip: u,
    delayDuration: r = Qw,
    skipDelayDuration: c = 300,
    disableHoverableContent: f = !1,
    children: m
  } = a, v = b.useRef(!0), g = b.useRef(!1), p = b.useRef(0);
  return b.useEffect(() => {
    const y = p.current;
    return () => window.clearTimeout(y);
  }, []), /* @__PURE__ */ k.jsx(
    Zw,
    {
      scope: u,
      isOpenDelayedRef: v,
      delayDuration: r,
      onOpen: b.useCallback(() => {
        c <= 0 || (window.clearTimeout(p.current), v.current = !1);
      }, [c]),
      onClose: b.useCallback(() => {
        c <= 0 || (window.clearTimeout(p.current), p.current = window.setTimeout(
          () => v.current = !0,
          c
        ));
      }, [c]),
      isPointerInTransitRef: g,
      onPointerInTransitChange: b.useCallback((y) => {
        g.current = y;
      }, []),
      disableHoverableContent: f,
      children: m
    }
  );
}, "TooltipProvider"), fd = "Tooltip", [Jw, Io] = jd(fd), Fw = /* @__PURE__ */ ge((a) => {
  const {
    __scopeTooltip: u,
    children: r,
    open: c,
    defaultOpen: f,
    onOpenChange: m,
    disableHoverableContent: v,
    delayDuration: g
  } = a, p = Ld(fd, a.__scopeTooltip), y = Bd(u), [S, d] = b.useState(null), [x, C] = b.useState(void 0), R = An(), O = b.useRef(0), N = v ?? p.disableHoverableContent, H = g ?? p.delayDuration, L = b.useRef(!1), [J, K] = yd({
    prop: c,
    defaultProp: f ?? !1,
    onChange: /* @__PURE__ */ ge((ht) => {
      ht ? (p.onOpen(), document.dispatchEvent(new CustomEvent(sd))) : p.onClose(), m == null || m(ht);
    }, "onChange"),
    caller: fd
  }), I = b.useMemo(() => J ? L.current ? "delayed-open" : "instant-open" : "closed", [J]), Z = b.useCallback(() => {
    window.clearTimeout(O.current), O.current = 0, L.current = !1, K(!0);
  }, [K]), X = b.useCallback(() => {
    window.clearTimeout(O.current), O.current = 0, K(!1);
  }, [K]), Y = b.useCallback(() => {
    window.clearTimeout(O.current), O.current = window.setTimeout(() => {
      L.current = !0, K(!0), O.current = 0;
    }, H);
  }, [H, K]);
  b.useEffect(() => () => {
    O.current && (window.clearTimeout(O.current), O.current = 0);
  }, []);
  const dt = x ?? R;
  return /* @__PURE__ */ k.jsx(Hw, { ...y, children: /* @__PURE__ */ k.jsx(
    Jw,
    {
      scope: u,
      contentId: dt,
      setContentId: C,
      open: J,
      stateAttribute: I,
      trigger: S,
      onTriggerChange: d,
      onTriggerEnter: b.useCallback(() => {
        p.isOpenDelayedRef.current ? Y() : Z();
      }, [p.isOpenDelayedRef, Y, Z]),
      onTriggerLeave: b.useCallback(() => {
        N ? X() : (window.clearTimeout(O.current), O.current = 0);
      }, [X, N]),
      onOpen: Z,
      onClose: X,
      disableHoverableContent: N,
      children: r
    }
  ) });
}, "Tooltip"), K0 = "TooltipTrigger", $w = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ ge(function(u, r) {
    const { __scopeTooltip: c, ...f } = u, m = Io(K0, c), v = Ld(K0, c), g = Bd(c), p = b.useRef(null), y = Fn(r, p, m.onTriggerChange), S = b.useRef(!1), d = b.useRef(!1), x = b.useCallback(() => S.current = !1, []);
    return b.useEffect(() => () => document.removeEventListener("pointerup", x), [x]), /* @__PURE__ */ k.jsx(jw, { asChild: !0, ...g, children: /* @__PURE__ */ k.jsx(
      se.button,
      {
        "aria-describedby": m.open ? m.contentId : void 0,
        "data-state": m.stateAttribute,
        ...f,
        ref: y,
        onPointerMove: ke(u.onPointerMove, (C) => {
          C.pointerType !== "touch" && !d.current && !v.isPointerInTransitRef.current && (m.onTriggerEnter(), d.current = !0);
        }),
        onPointerLeave: ke(u.onPointerLeave, () => {
          m.onTriggerLeave(), d.current = !1;
        }),
        onPointerDown: ke(u.onPointerDown, () => {
          m.open && m.onClose(), S.current = !0, document.addEventListener("pointerup", x, { once: !0 });
        }),
        onFocus: ke(u.onFocus, () => {
          S.current || m.onOpen();
        }),
        onBlur: ke(u.onBlur, m.onClose),
        onClick: ke(u.onClick, m.onClose)
      }
    ) });
  }, "TooltipTrigger")
), Fp = "TooltipPortal", [Iw, Pw] = jd(Fp, {
  forceMount: void 0
}), Ww = /* @__PURE__ */ ge((a) => {
  const { __scopeTooltip: u, forceMount: r, children: c, container: f } = a, m = Io(Fp, u);
  return /* @__PURE__ */ k.jsx(Iw, { scope: u, forceMount: r, children: /* @__PURE__ */ k.jsx(Fo, { present: r || m.open, children: /* @__PURE__ */ k.jsx(ky, { asChild: !0, container: f, children: c }) }) });
}, "TooltipPortal"), Zo = "TooltipContent", tC = /* @__PURE__ */ b.forwardRef(
  /* @__PURE__ */ ge(function(u, r) {
    const c = Pw(Zo, u.__scopeTooltip), { forceMount: f = c.forceMount, side: m = "top", ...v } = u, g = Io(Zo, u.__scopeTooltip);
    return /* @__PURE__ */ k.jsx(Fo, { present: f || g.open, children: g.disableHoverableContent ? /* @__PURE__ */ k.jsx($p, { side: m, ...v, ref: r }) : /* @__PURE__ */ k.jsx(eC, { side: m, ...v, ref: r }) });
  }, "TooltipContent")
), eC = /* @__PURE__ */ b.forwardRef(/* @__PURE__ */ ge(function(u, r) {
  const c = Io(Zo, u.__scopeTooltip), f = Ld(Zo, u.__scopeTooltip), m = b.useRef(null), v = Fn(r, m), [g, p] = b.useState(null), { trigger: y, onClose: S } = c, d = m.current, { onPointerInTransitChange: x } = f, C = b.useCallback(() => {
    p(null), x(!1);
  }, [x]), R = b.useCallback(
    (O, N) => {
      const H = O.currentTarget, L = { x: O.clientX, y: O.clientY }, J = Ip(L, H.getBoundingClientRect()), K = Pp(L, J), I = Wp(N.getBoundingClientRect()), Z = eb([...K, ...I]);
      p(Z), x(!0);
    },
    [x]
  );
  return b.useEffect(() => () => C(), [C]), b.useEffect(() => {
    if (y && d) {
      const O = /* @__PURE__ */ ge((H) => R(H, d), "handleTriggerLeave"), N = /* @__PURE__ */ ge((H) => R(H, y), "handleContentLeave");
      return y.addEventListener("pointerleave", O), d.addEventListener("pointerleave", N), () => {
        y.removeEventListener("pointerleave", O), d.removeEventListener("pointerleave", N);
      };
    }
  }, [y, d, R, C]), b.useEffect(() => {
    if (g) {
      const O = /* @__PURE__ */ ge((N) => {
        const H = N.target, L = { x: N.clientX, y: N.clientY }, J = (y == null ? void 0 : y.contains(H)) || (d == null ? void 0 : d.contains(H)), K = !tb(L, g);
        J ? C() : K && (C(), S());
      }, "handleTrackPointerGrace");
      return document.addEventListener("pointermove", O), () => document.removeEventListener("pointermove", O);
    }
  }, [y, d, g, S, C]), /* @__PURE__ */ k.jsx($p, { ...u, ref: v });
}, "TooltipContentHoverable")), nC = /* @__PURE__ */ ly("TooltipContent"), $p = /* @__PURE__ */ b.forwardRef(
  // blank line to reduce diff noise
  /* @__PURE__ */ ge(function(u, r) {
    const {
      __scopeTooltip: c,
      children: f,
      "aria-label": m,
      id: v,
      onEscapeKeyDown: g,
      onPointerDownOutside: p,
      ...y
    } = u, S = Io(Zo, c), d = Bd(c), { onClose: x } = S;
    b.useEffect(() => (document.addEventListener(sd, x), () => document.removeEventListener(sd, x)), [x]), b.useEffect(() => {
      if (S.trigger) {
        const R = /* @__PURE__ */ ge((O) => {
          O.target instanceof Node && O.target.contains(S.trigger) && x();
        }, "handleScroll");
        return window.addEventListener("scroll", R, { capture: !0 }), () => window.removeEventListener("scroll", R, { capture: !0 });
      }
    }, [S.trigger, x]);
    const { setContentId: C } = S;
    return ln(() => (C(v), () => {
      C(void 0);
    }), [v, C]), /* @__PURE__ */ k.jsx(
      Uy,
      {
        asChild: !0,
        disableOutsidePointerEvents: !1,
        onEscapeKeyDown: g,
        onPointerDownOutside: p,
        onFocusOutside: (R) => R.preventDefault(),
        onDismiss: x,
        children: /* @__PURE__ */ k.jsxs(
          Bw,
          {
            "data-state": S.stateAttribute,
            role: m ? void 0 : "tooltip",
            id: m ? void 0 : S.contentId,
            ...d,
            ...y,
            ref: r,
            style: {
              ...y.style,
              "--radix-tooltip-content-transform-origin": "var(--radix-popper-transform-origin)",
              "--radix-tooltip-content-available-width": "var(--radix-popper-available-width)",
              "--radix-tooltip-content-available-height": "var(--radix-popper-available-height)",
              "--radix-tooltip-trigger-width": "var(--radix-popper-anchor-width)",
              "--radix-tooltip-trigger-height": "var(--radix-popper-anchor-height)"
            },
            children: [
              /* @__PURE__ */ k.jsx(nC, { children: f }),
              m ? /* @__PURE__ */ k.jsx(Gw, { id: S.contentId, role: "tooltip", children: m }) : null
            ]
          }
        )
      }
    );
  }, "TooltipContentImpl")
);
function Ip(a, u) {
  const r = Math.abs(u.top - a.y), c = Math.abs(u.bottom - a.y), f = Math.abs(u.right - a.x), m = Math.abs(u.left - a.x);
  switch (Math.min(r, c, f, m)) {
    case m:
      return "left";
    case f:
      return "right";
    case r:
      return "top";
    case c:
      return "bottom";
    default:
      throw new Error("unreachable");
  }
}
ge(Ip, "getExitSideFromRect");
function Pp(a, u, r = 5) {
  const c = [];
  switch (u) {
    case "top":
      c.push(
        { x: a.x - r, y: a.y + r },
        { x: a.x + r, y: a.y + r }
      );
      break;
    case "bottom":
      c.push(
        { x: a.x - r, y: a.y - r },
        { x: a.x + r, y: a.y - r }
      );
      break;
    case "left":
      c.push(
        { x: a.x + r, y: a.y - r },
        { x: a.x + r, y: a.y + r }
      );
      break;
    case "right":
      c.push(
        { x: a.x - r, y: a.y - r },
        { x: a.x - r, y: a.y + r }
      );
      break;
  }
  return c;
}
ge(Pp, "getPaddedExitPoints");
function Wp(a) {
  const { top: u, right: r, bottom: c, left: f } = a;
  return [
    { x: f, y: u },
    { x: r, y: u },
    { x: r, y: c },
    { x: f, y: c }
  ];
}
ge(Wp, "getPointsFromRect");
function tb(a, u) {
  const { x: r, y: c } = a;
  let f = !1;
  for (let m = 0, v = u.length - 1; m < u.length; v = m++) {
    const g = u[m], p = u[v], y = g.x, S = g.y, d = p.x, x = p.y;
    S > c != x > c && r < (d - y) * (c - S) / (x - S) + y && (f = !f);
  }
  return f;
}
ge(tb, "isPointInPolygon");
function eb(a) {
  const u = a.slice();
  return u.sort((r, c) => r.x < c.x ? -1 : r.x > c.x ? 1 : r.y < c.y ? -1 : r.y > c.y ? 1 : 0), nb(u);
}
ge(eb, "getHull");
function nb(a) {
  if (a.length <= 1) return a.slice();
  const u = [];
  for (let c = 0; c < a.length; c++) {
    const f = a[c];
    for (; u.length >= 2; ) {
      const m = u[u.length - 1], v = u[u.length - 2];
      if ((m.x - v.x) * (f.y - v.y) >= (m.y - v.y) * (f.x - v.x)) u.pop();
      else break;
    }
    u.push(f);
  }
  u.pop();
  const r = [];
  for (let c = a.length - 1; c >= 0; c--) {
    const f = a[c];
    for (; r.length >= 2; ) {
      const m = r[r.length - 1], v = r[r.length - 2];
      if ((m.x - v.x) * (f.y - v.y) >= (m.y - v.y) * (f.x - v.x)) r.pop();
      else break;
    }
    r.push(f);
  }
  return r.pop(), u.length === 1 && r.length === 1 && u[0].x === r[0].x && u[0].y === r[0].y ? u : u.concat(r);
}
ge(nb, "getHullPresorted");
var lC = Kw, aC = Fw, iC = $w, oC = Ww, lb = tC;
const uC = lC, rC = aC, cC = iC, ab = b.forwardRef(({ className: a, sideOffset: u = 4, ...r }, c) => /* @__PURE__ */ k.jsx(oC, { children: /* @__PURE__ */ k.jsx(
  lb,
  {
    ref: c,
    sideOffset: u,
    className: Ze(
      "z-50 overflow-hidden rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-tooltip-content-transform-origin]",
      a
    ),
    ...r
  }
) }));
ab.displayName = lb.displayName;
function sC(a) {
  if (typeof document > "u") return;
  let u = document.head || document.getElementsByTagName("head")[0], r = document.createElement("style");
  r.type = "text/css", u.appendChild(r), r.styleSheet ? r.styleSheet.cssText = a : r.appendChild(document.createTextNode(a));
}
const fC = (a) => {
  switch (a) {
    case "success":
      return vC;
    case "info":
      return gC;
    case "warning":
      return hC;
    case "error":
      return yC;
    default:
      return null;
  }
}, dC = Array(12).fill(0), mC = ({ visible: a, className: u }) => /* @__PURE__ */ et.createElement("div", {
  className: [
    "sonner-loading-wrapper",
    u
  ].filter(Boolean).join(" "),
  "data-visible": a
}, /* @__PURE__ */ et.createElement("div", {
  className: "sonner-spinner"
}, dC.map((r, c) => /* @__PURE__ */ et.createElement("div", {
  className: "sonner-loading-bar",
  key: `spinner-bar-${c}`
})))), vC = /* @__PURE__ */ et.createElement("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  viewBox: "0 0 20 20",
  fill: "currentColor",
  height: "20",
  width: "20",
  "aria-hidden": "true"
}, /* @__PURE__ */ et.createElement("path", {
  fillRule: "evenodd",
  d: "M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z",
  clipRule: "evenodd"
})), hC = /* @__PURE__ */ et.createElement("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  viewBox: "0 0 24 24",
  fill: "currentColor",
  height: "20",
  width: "20",
  "aria-hidden": "true"
}, /* @__PURE__ */ et.createElement("path", {
  fillRule: "evenodd",
  d: "M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z",
  clipRule: "evenodd"
})), gC = /* @__PURE__ */ et.createElement("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  viewBox: "0 0 20 20",
  fill: "currentColor",
  height: "20",
  width: "20",
  "aria-hidden": "true"
}, /* @__PURE__ */ et.createElement("path", {
  fillRule: "evenodd",
  d: "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z",
  clipRule: "evenodd"
})), yC = /* @__PURE__ */ et.createElement("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  viewBox: "0 0 20 20",
  fill: "currentColor",
  height: "20",
  width: "20",
  "aria-hidden": "true"
}, /* @__PURE__ */ et.createElement("path", {
  fillRule: "evenodd",
  d: "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z",
  clipRule: "evenodd"
})), pC = /* @__PURE__ */ et.createElement("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  width: "12",
  height: "12",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: "1.5",
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": "true"
}, /* @__PURE__ */ et.createElement("line", {
  x1: "18",
  y1: "6",
  x2: "6",
  y2: "18"
}), /* @__PURE__ */ et.createElement("line", {
  x1: "6",
  y1: "6",
  x2: "18",
  y2: "18"
})), bC = () => {
  const [a, u] = et.useState(document.hidden);
  return et.useEffect(() => {
    const r = () => {
      u(document.hidden);
    };
    return document.addEventListener("visibilitychange", r), () => document.removeEventListener("visibilitychange", r);
  }, []), a;
};
let SC = 1;
const EC = 100, J0 = (a) => {
  var u;
  return typeof (a == null ? void 0 : a.id) == "number" || (a == null || (u = a.id) == null ? void 0 : u.length) > 0 ? a.id : SC++;
};
class xC {
  constructor() {
    this.subscribe = (u) => (this.subscribers.push(u), this.getActiveToasts().forEach((r) => u(r)), () => {
      const r = this.subscribers.indexOf(u);
      this.subscribers.splice(r, 1);
    }), this.publish = (u) => {
      this.subscribers.forEach((r) => r(u));
    }, this.addToast = (u) => {
      this.publish(u), this.toasts = [
        ...this.toasts,
        u
      ], this.trimHistory();
    }, this.trimHistory = () => {
      let u = this.toasts.length - EC;
      u <= 0 || (this.toasts = this.toasts.filter((r) => u > 0 && this.dismissedToasts.has(r.id) ? (this.dismissedToasts.delete(r.id), u--, !1) : !0));
    }, this.create = (u) => {
      const { message: r, ...c } = u, f = J0(u), m = this.pendingDismissals.get(f);
      m !== void 0 && (cancelAnimationFrame(m), this.pendingDismissals.delete(f), this.dismissedToasts.delete(f));
      const v = this.dismissedToasts.has(f), g = u.dismissible === void 0 ? !0 : u.dismissible;
      return v && (this.dismissedToasts.delete(f), this.toasts = this.toasts.filter((y) => y.id !== f)), (v ? void 0 : this.toasts.find((y) => y.id === f)) ? this.toasts = this.toasts.map((y) => y.id === f ? (this.publish({
        ...y,
        ...u,
        id: f,
        title: r
      }), {
        ...y,
        ...u,
        id: f,
        dismissible: g,
        title: r
      }) : y) : this.addToast({
        title: r,
        ...c,
        dismissible: g,
        id: f
      }), f;
    }, this.dismiss = (u) => {
      if (u == null)
        return this.getActiveToasts().forEach((c) => {
          this.dismissedToasts.add(c.id), this.subscribers.forEach((f) => f({
            id: c.id,
            dismiss: !0
          }));
        }), u;
      this.dismissedToasts.add(u);
      const r = this.pendingDismissals.get(u);
      return r !== void 0 && cancelAnimationFrame(r), this.pendingDismissals.set(u, requestAnimationFrame(() => {
        this.pendingDismissals.delete(u), this.subscribers.forEach((c) => c({
          id: u,
          dismiss: !0
        }));
      })), u;
    }, this.message = (u, r) => this.create({
      ...r,
      message: u,
      type: void 0
    }), this.error = (u, r) => this.create({
      ...r,
      message: u,
      type: "error"
    }), this.success = (u, r) => this.create({
      ...r,
      type: "success",
      message: u
    }), this.info = (u, r) => this.create({
      ...r,
      type: "info",
      message: u
    }), this.warning = (u, r) => this.create({
      ...r,
      type: "warning",
      message: u
    }), this.loading = (u, r) => this.create({
      ...r,
      type: "loading",
      message: u
    }), this.promise = (u, r) => {
      if (!r)
        return;
      let c;
      r.loading !== void 0 && (c = this.create({
        ...r,
        promise: u,
        type: "loading",
        message: r.loading,
        description: typeof r.description != "function" ? r.description : void 0
      }));
      const f = Promise.resolve(u instanceof Function ? u() : u);
      let m = c !== void 0, v;
      const g = f.then(async (y) => {
        if (v = [
          "resolve",
          y
        ], et.isValidElement(y))
          m = !1, this.create({
            id: c,
            type: "default",
            message: y
          });
        else if (wC(y) && !y.ok) {
          m = !1;
          const d = typeof r.error == "function" ? await r.error(`HTTP error! status: ${y.status}`) : r.error, x = typeof r.description == "function" ? await r.description(`HTTP error! status: ${y.status}`) : r.description, R = typeof d == "object" && !et.isValidElement(d) ? d : {
            message: d
          };
          this.create({
            id: c,
            type: "error",
            description: x,
            ...R
          });
        } else if (y instanceof Error) {
          m = !1;
          const d = typeof r.error == "function" ? await r.error(y) : r.error, x = typeof r.description == "function" ? await r.description(y) : r.description, R = typeof d == "object" && !et.isValidElement(d) ? d : {
            message: d
          };
          this.create({
            id: c,
            type: "error",
            description: x,
            ...R
          });
        } else if (r.success !== void 0) {
          m = !1;
          const d = typeof r.success == "function" ? await r.success(y) : r.success, x = typeof r.description == "function" ? await r.description(y) : r.description, R = typeof d == "object" && !et.isValidElement(d) ? d : {
            message: d
          };
          this.create({
            id: c,
            type: "success",
            description: x,
            ...R
          });
        }
      }).catch(async (y) => {
        if (v = [
          "reject",
          y
        ], r.error !== void 0) {
          m = !1;
          const S = typeof r.error == "function" ? await r.error(y) : r.error, d = typeof r.description == "function" ? await r.description(y) : r.description, C = typeof S == "object" && !et.isValidElement(S) ? S : {
            message: S
          };
          this.create({
            id: c,
            type: "error",
            description: d,
            ...C
          });
        }
      }).finally(() => {
        m && (this.dismiss(c), c = void 0), r.finally == null || r.finally.call(r);
      }), p = () => new Promise((y, S) => g.then(() => v[0] === "reject" ? S(v[1]) : y(v[1])).catch(S));
      return typeof c != "string" && typeof c != "number" ? {
        unwrap: p
      } : Object.assign(c, {
        unwrap: p
      });
    }, this.custom = (u, r) => {
      const c = J0(r);
      return this.create({
        ...r,
        jsx: u(c),
        id: c,
        type: void 0
      }), c;
    }, this.getActiveToasts = () => this.toasts.filter((u) => !this.dismissedToasts.has(u.id)), this.subscribers = [], this.toasts = [], this.dismissedToasts = /* @__PURE__ */ new Set(), this.pendingDismissals = /* @__PURE__ */ new Map();
  }
}
const Xe = new xC(), TC = (a, u) => Xe.message(a, u), wC = (a) => a && typeof a == "object" && "ok" in a && typeof a.ok == "boolean" && "status" in a && typeof a.status == "number", CC = TC, OC = () => Xe.toasts, _C = () => Xe.getActiveToasts(), AC = Object.assign(CC, {
  success: Xe.success,
  info: Xe.info,
  warning: Xe.warning,
  error: Xe.error,
  custom: Xe.custom,
  message: Xe.message,
  promise: Xe.promise,
  dismiss: Xe.dismiss,
  loading: Xe.loading
}, {
  getHistory: OC,
  getToasts: _C
});
sC("[data-sonner-toaster][dir=ltr],html[dir=ltr]{--toast-icon-margin-start:-3px;--toast-icon-margin-end:4px;--toast-svg-margin-start:-1px;--toast-svg-margin-end:0px;--toast-button-margin-start:auto;--toast-button-margin-end:0;--toast-close-button-start:0;--toast-close-button-end:unset;--toast-close-button-transform:translate(-35%, -35%)}[data-sonner-toaster][dir=rtl],html[dir=rtl]{--toast-icon-margin-start:4px;--toast-icon-margin-end:-3px;--toast-svg-margin-start:0px;--toast-svg-margin-end:-1px;--toast-button-margin-start:0;--toast-button-margin-end:auto;--toast-close-button-start:unset;--toast-close-button-end:0;--toast-close-button-transform:translate(35%, -35%)}[data-sonner-toaster]{position:fixed;width:var(--width);font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji;--gray1:hsl(0, 0%, 99%);--gray2:hsl(0, 0%, 97.3%);--gray3:hsl(0, 0%, 95.1%);--gray4:hsl(0, 0%, 93%);--gray5:hsl(0, 0%, 90.9%);--gray6:hsl(0, 0%, 88.7%);--gray7:hsl(0, 0%, 85.8%);--gray8:hsl(0, 0%, 78%);--gray9:hsl(0, 0%, 56.1%);--gray10:hsl(0, 0%, 52.3%);--gray11:hsl(0, 0%, 43.5%);--gray12:hsl(0, 0%, 9%);--border-radius:8px;box-sizing:border-box;padding:0;margin:0;list-style:none;outline:0;z-index:999999999;transition:transform .4s ease}@media (hover:none) and (pointer:coarse){[data-sonner-toaster][data-lifted=true]{transform:none}}[data-sonner-toaster][data-x-position=right]{right:var(--offset-right)}[data-sonner-toaster][data-x-position=left]{left:var(--offset-left)}[data-sonner-toaster][data-x-position=center]{left:50%;transform:translateX(-50%)}[data-sonner-toaster][data-y-position=top]{top:var(--offset-top)}[data-sonner-toaster][data-y-position=bottom]{bottom:var(--offset-bottom)}[data-sonner-toast]{--y:translateY(100%);--lift-amount:calc(var(--lift) * var(--gap));z-index:var(--z-index);position:absolute;opacity:0;transform:var(--y);touch-action:none;transition:transform .4s,opacity .4s,height .4s,box-shadow .2s;box-sizing:border-box;outline:0;overflow-wrap:anywhere}[data-sonner-toast][data-styled=true]{padding:16px;background:var(--normal-bg);border:1px solid var(--normal-border);color:var(--normal-text);border-radius:var(--border-radius);box-shadow:0 4px 12px rgba(0,0,0,.1);width:var(--width);font-size:13px;display:flex;align-items:center;gap:6px}[data-sonner-toast]:focus-visible{box-shadow:0 4px 12px rgba(0,0,0,.1),0 0 0 2px rgba(0,0,0,.2)}[data-sonner-toast][data-y-position=top]{top:0;--y:translateY(-100%);--lift:1;--lift-amount:calc(1 * var(--gap))}[data-sonner-toast][data-y-position=bottom]{bottom:0;--y:translateY(100%);--lift:-1;--lift-amount:calc(var(--lift) * var(--gap))}[data-sonner-toast][data-styled=true] [data-description]{font-weight:400;line-height:1.4;color:#3f3f3f}[data-rich-colors=true][data-sonner-toast][data-styled=true] [data-description]{color:inherit}[data-sonner-toaster][data-sonner-theme=dark] [data-description]{color:#e8e8e8}[data-sonner-toast][data-styled=true] [data-title]{font-weight:500;line-height:1.5;color:inherit}[data-sonner-toast][data-styled=true] [data-icon]{display:flex;height:16px;width:16px;position:relative;justify-content:flex-start;align-items:center;flex-shrink:0;margin-left:var(--toast-icon-margin-start);margin-right:var(--toast-icon-margin-end)}[data-sonner-toast][data-promise=true] [data-icon]>svg{opacity:0;transform:scale(.8);transform-origin:center;animation:sonner-fade-in .3s ease forwards}[data-sonner-toast][data-styled=true] [data-icon]>*{flex-shrink:0}[data-sonner-toast][data-styled=true] [data-icon] svg{margin-left:var(--toast-svg-margin-start);margin-right:var(--toast-svg-margin-end)}[data-sonner-toast][data-styled=true] [data-content]{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0}[data-sonner-toast][data-styled=true] [data-button]{border-radius:4px;padding-left:8px;padding-right:8px;height:24px;font-size:12px;color:var(--normal-bg);background:var(--normal-text);margin-left:var(--toast-button-margin-start);margin-right:var(--toast-button-margin-end);border:none;font-weight:500;cursor:pointer;outline:0;display:flex;align-items:center;flex-shrink:0;transition:opacity .4s,box-shadow .2s}[data-sonner-toast][data-styled=true] [data-button]:focus-visible{box-shadow:0 0 0 2px rgba(0,0,0,.4)}[data-sonner-toast][data-styled=true] [data-button]:first-of-type{margin-left:var(--toast-button-margin-start);margin-right:var(--toast-button-margin-end)}[data-sonner-toast][data-styled=true] [data-cancel]{color:var(--normal-text);background:rgba(0,0,0,.08)}[data-sonner-toaster][data-sonner-theme=dark] [data-sonner-toast][data-styled=true] [data-cancel]{background:rgba(255,255,255,.3)}[data-sonner-toast][data-styled=true] [data-close-button]{position:absolute;left:var(--toast-close-button-start);right:var(--toast-close-button-end);top:0;height:20px;width:20px;display:flex;justify-content:center;align-items:center;padding:0;color:var(--normal-text);background:var(--normal-bg);border:1px solid var(--normal-border);transform:var(--toast-close-button-transform);border-radius:50%;cursor:pointer;z-index:1;transition:opacity .1s,background .2s,border-color .2s}[data-sonner-toast][data-styled=true] [data-close-button]:focus-visible{box-shadow:0 4px 12px rgba(0,0,0,.1),0 0 0 2px rgba(0,0,0,.2)}[data-sonner-toast][data-styled=true] [data-disabled=true]{cursor:not-allowed}[data-sonner-toast][data-styled=true]:hover [data-close-button]:hover{background:var(--gray2);border-color:var(--gray5)}[data-sonner-toast][data-swiping=true]::before{content:'';position:absolute;left:-100%;right:-100%;height:100%;z-index:-1}[data-sonner-toast][data-y-position=top][data-swiping=true]::before{bottom:50%;transform:scaleY(3) translateY(50%)}[data-sonner-toast][data-y-position=bottom][data-swiping=true]::before{top:50%;transform:scaleY(3) translateY(-50%)}[data-sonner-toast][data-swiping=false][data-removed=true]::before{content:'';position:absolute;inset:0;transform:scaleY(2)}[data-sonner-toast][data-expanded=true]::after{content:'';position:absolute;left:0;height:calc(var(--gap) + 1px);bottom:100%;width:100%}[data-sonner-toast][data-mounted=true]{--y:translateY(0);opacity:1}[data-sonner-toast][data-expanded=false][data-front=false]{--scale:var(--toasts-before) * 0.05 + 1;--y:translateY(calc(var(--lift-amount) * var(--toasts-before))) scale(calc(-1 * var(--scale)));height:var(--front-toast-height)}[data-sonner-toast]>*{transition:opacity .4s}[data-sonner-toast][data-x-position=right]{right:0}[data-sonner-toast][data-x-position=left]{left:0}[data-sonner-toast][data-expanded=false][data-front=false][data-styled=true]>*{opacity:0}[data-sonner-toast][data-visible=false]{opacity:0;pointer-events:none}[data-sonner-toast][data-mounted=true][data-expanded=true]{--y:translateY(calc(var(--lift) * var(--offset)));height:var(--initial-height)}[data-sonner-toast][data-removed=true][data-front=true][data-swipe-out=false]{--y:translateY(calc(var(--lift) * -100%));opacity:0}[data-sonner-toast][data-removed=true][data-front=false][data-swipe-out=false][data-expanded=true]{--y:translateY(calc(var(--lift) * var(--offset) + var(--lift) * -100%));opacity:0}[data-sonner-toast][data-removed=true][data-front=false][data-swipe-out=false][data-expanded=false]{--y:translateY(40%);opacity:0;transition:transform .5s,opacity .2s}[data-sonner-toast][data-removed=true][data-front=false]::before{height:calc(var(--initial-height) + 20%)}[data-sonner-toast][data-swiping=true]{transform:var(--y) translateY(var(--swipe-amount-y,0)) translateX(var(--swipe-amount-x,0));transition:none}[data-sonner-toast][data-swiped=true]{-webkit-user-select:none;user-select:none}[data-sonner-toast][data-swipe-out=true][data-y-position=bottom],[data-sonner-toast][data-swipe-out=true][data-y-position=top]{animation-duration:.2s;animation-timing-function:ease-out;animation-fill-mode:forwards}[data-sonner-toast][data-swipe-out=true][data-swipe-direction=left]{animation-name:swipe-out-left}[data-sonner-toast][data-swipe-out=true][data-swipe-direction=right]{animation-name:swipe-out-right}[data-sonner-toast][data-swipe-out=true][data-swipe-direction=up]{animation-name:swipe-out-up}[data-sonner-toast][data-swipe-out=true][data-swipe-direction=down]{animation-name:swipe-out-down}@keyframes swipe-out-left{from{transform:var(--y) translateX(var(--swipe-amount-x));opacity:1}to{transform:var(--y) translateX(calc(var(--swipe-amount-x) - 100%));opacity:0}}@keyframes swipe-out-right{from{transform:var(--y) translateX(var(--swipe-amount-x));opacity:1}to{transform:var(--y) translateX(calc(var(--swipe-amount-x) + 100%));opacity:0}}@keyframes swipe-out-up{from{transform:var(--y) translateY(var(--swipe-amount-y));opacity:1}to{transform:var(--y) translateY(calc(var(--swipe-amount-y) - 100%));opacity:0}}@keyframes swipe-out-down{from{transform:var(--y) translateY(var(--swipe-amount-y));opacity:1}to{transform:var(--y) translateY(calc(var(--swipe-amount-y) + 100%));opacity:0}}@media (max-width:600px){[data-sonner-toaster]{position:fixed;right:var(--mobile-offset-right);left:var(--mobile-offset-left);width:100%}[data-sonner-toaster][dir=rtl]{left:calc(var(--mobile-offset-left) * -1)}[data-sonner-toaster] [data-sonner-toast]{left:0;right:0;width:calc(100% - var(--mobile-offset-left) * 2)}[data-sonner-toaster][data-x-position=left]{left:var(--mobile-offset-left)}[data-sonner-toaster][data-y-position=bottom]{bottom:var(--mobile-offset-bottom)}[data-sonner-toaster][data-y-position=top]{top:var(--mobile-offset-top)}[data-sonner-toaster][data-x-position=center]{left:var(--mobile-offset-left);right:var(--mobile-offset-right);transform:none}}[data-sonner-toaster][data-sonner-theme=light]{--normal-bg:#fff;--normal-border:var(--gray4);--normal-text:var(--gray12);--success-bg:hsl(143, 85%, 96%);--success-border:hsl(145, 92%, 87%);--success-text:hsl(140, 100%, 27%);--info-bg:hsl(208, 100%, 97%);--info-border:hsl(221, 91%, 93%);--info-text:hsl(210, 92%, 45%);--warning-bg:hsl(49, 100%, 97%);--warning-border:hsl(49, 91%, 84%);--warning-text:hsl(31, 92%, 45%);--error-bg:hsl(359, 100%, 97%);--error-border:hsl(359, 100%, 94%);--error-text:hsl(360, 100%, 45%)}[data-sonner-toaster][data-sonner-theme=light] [data-sonner-toast][data-invert=true]{--normal-bg:#000;--normal-border:hsl(0, 0%, 20%);--normal-text:var(--gray1)}[data-sonner-toaster][data-sonner-theme=dark] [data-sonner-toast][data-invert=true]{--normal-bg:#fff;--normal-border:var(--gray3);--normal-text:var(--gray12)}[data-sonner-toaster][data-sonner-theme=dark]{--normal-bg:#000;--normal-bg-hover:hsl(0, 0%, 12%);--normal-border:hsl(0, 0%, 20%);--normal-border-hover:hsl(0, 0%, 25%);--normal-text:var(--gray1);--success-bg:hsl(150, 100%, 6%);--success-border:hsl(147, 100%, 12%);--success-text:hsl(150, 86%, 65%);--info-bg:hsl(215, 100%, 6%);--info-border:hsl(223, 43%, 17%);--info-text:hsl(216, 87%, 65%);--warning-bg:hsl(64, 100%, 6%);--warning-border:hsl(60, 100%, 9%);--warning-text:hsl(46, 87%, 65%);--error-bg:hsl(358, 76%, 10%);--error-border:hsl(357, 89%, 16%);--error-text:hsl(358, 100%, 81%)}[data-sonner-toaster][data-sonner-theme=dark] [data-sonner-toast] [data-close-button]{background:var(--normal-bg);border-color:var(--normal-border);color:var(--normal-text)}[data-sonner-toaster][data-sonner-theme=dark] [data-sonner-toast] [data-close-button]:hover{background:var(--normal-bg-hover);border-color:var(--normal-border-hover)}[data-rich-colors=true][data-sonner-toast][data-type=success]{background:var(--success-bg);border-color:var(--success-border);color:var(--success-text)}[data-rich-colors=true][data-sonner-toast][data-type=success] [data-close-button]{background:var(--success-bg);border-color:var(--success-border);color:var(--success-text)}[data-rich-colors=true][data-sonner-toast][data-type=info]{background:var(--info-bg);border-color:var(--info-border);color:var(--info-text)}[data-rich-colors=true][data-sonner-toast][data-type=info] [data-close-button]{background:var(--info-bg);border-color:var(--info-border);color:var(--info-text)}[data-rich-colors=true][data-sonner-toast][data-type=warning]{background:var(--warning-bg);border-color:var(--warning-border);color:var(--warning-text)}[data-rich-colors=true][data-sonner-toast][data-type=warning] [data-close-button]{background:var(--warning-bg);border-color:var(--warning-border);color:var(--warning-text)}[data-rich-colors=true][data-sonner-toast][data-type=error]{background:var(--error-bg);border-color:var(--error-border);color:var(--error-text)}[data-rich-colors=true][data-sonner-toast][data-type=error] [data-close-button]{background:var(--error-bg);border-color:var(--error-border);color:var(--error-text)}.sonner-loading-wrapper{--size:16px;height:var(--size);width:var(--size);position:absolute;inset:0;z-index:10}.sonner-loading-wrapper[data-visible=false]{transform-origin:center;animation:sonner-fade-out .2s ease forwards}.sonner-spinner{position:relative;top:50%;left:50%;height:var(--size);width:var(--size)}.sonner-loading-bar{animation:sonner-spin 1.2s linear infinite;background:var(--gray11);border-radius:6px;height:8%;left:-10%;position:absolute;top:-3.9%;width:24%}.sonner-loading-bar:first-child{animation-delay:-1.2s;transform:rotate(.0001deg) translate(146%)}.sonner-loading-bar:nth-child(2){animation-delay:-1.1s;transform:rotate(30deg) translate(146%)}.sonner-loading-bar:nth-child(3){animation-delay:-1s;transform:rotate(60deg) translate(146%)}.sonner-loading-bar:nth-child(4){animation-delay:-.9s;transform:rotate(90deg) translate(146%)}.sonner-loading-bar:nth-child(5){animation-delay:-.8s;transform:rotate(120deg) translate(146%)}.sonner-loading-bar:nth-child(6){animation-delay:-.7s;transform:rotate(150deg) translate(146%)}.sonner-loading-bar:nth-child(7){animation-delay:-.6s;transform:rotate(180deg) translate(146%)}.sonner-loading-bar:nth-child(8){animation-delay:-.5s;transform:rotate(210deg) translate(146%)}.sonner-loading-bar:nth-child(9){animation-delay:-.4s;transform:rotate(240deg) translate(146%)}.sonner-loading-bar:nth-child(10){animation-delay:-.3s;transform:rotate(270deg) translate(146%)}.sonner-loading-bar:nth-child(11){animation-delay:-.2s;transform:rotate(300deg) translate(146%)}.sonner-loading-bar:nth-child(12){animation-delay:-.1s;transform:rotate(330deg) translate(146%)}@keyframes sonner-fade-in{0%{opacity:0;transform:scale(.8)}100%{opacity:1;transform:scale(1)}}@keyframes sonner-fade-out{0%{opacity:1;transform:scale(1)}100%{opacity:0;transform:scale(.8)}}@keyframes sonner-spin{0%{opacity:1}100%{opacity:.15}}@media (prefers-reduced-motion){.sonner-loading-bar,[data-sonner-toast],[data-sonner-toast]>*{transition:none!important;animation:none!important}}.sonner-loader{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);transform-origin:center;transition:opacity .2s,transform .2s}.sonner-loader[data-visible=false]{opacity:0;transform:scale(.8) translate(-50%,-50%)}");
function Hr(a) {
  return a.label !== void 0;
}
const RC = 3, NC = "24px", DC = "16px", F0 = 4e3, zC = 356, MC = 14, UC = 45, HC = 200;
function kn(...a) {
  return a.filter(Boolean).join(" ");
}
function jC(a) {
  const [u, r] = a.split("-"), c = [];
  return u && c.push(u), r && c.push(r), c;
}
const BC = (a) => {
  var u, r, c, f, m, v, g, p, y;
  const { invert: S, toast: d, unstyled: x, interacting: C, setHeights: R, visibleToasts: O, heights: N, index: H, toasts: L, expanded: J, removeToast: K, defaultRichColors: I, closeButton: Z, style: X, cancelButtonStyle: Y, actionButtonStyle: dt, className: ht = "", descriptionClassName: xt = "", duration: st, position: Tt, gap: gt, expandByDefault: yt, classNames: B, icons: tt, closeButtonAriaLabel: P = "Close toast" } = a, [at, F] = et.useState(null), [Bt, Q] = et.useState(null), [rt, E] = et.useState(!1), [_, V] = et.useState(!1), [$, ft] = et.useState(!1), [W, bt] = et.useState(!1), [lt, mt] = et.useState(!1), [It, _e] = et.useState(0), [bn, ye] = et.useState(0), Qt = et.useRef(d.duration || st || F0), Ut = et.useRef(null), Pt = et.useRef(null), In = H === 0, an = H + 1 <= O, Jt = d.type, na = Jt ?? "default", Je = d.dismissible !== !1, Li = d.className || "", Ha = d.descriptionClassName || "", El = et.useMemo(() => N.findIndex((St) => St.toastId === d.id) || 0, [
    N,
    d.id
  ]), Po = et.useMemo(() => {
    var St;
    return (St = d.closeButton) != null ? St : Z;
  }, [
    d.closeButton,
    Z
  ]), Sn = et.useMemo(() => d.duration || st || F0, [
    d.duration,
    st
  ]), la = et.useRef(0), Nn = et.useRef(0), Wo = et.useRef(0), Pn = et.useRef(null), [Yi, qi] = Tt.split("-"), ja = et.useMemo(() => N.reduce((St, le, Wt) => Wt >= El ? St : St + le.height, 0), [
    N,
    El
  ]), tu = bC(), on = et.useMemo(() => {
    var St;
    return (St = a.swipeDirections) != null ? St : jC(Tt);
  }, [
    a.swipeDirections,
    Tt
  ]), Ae = d.invert || S, Vi = Jt === "loading";
  Nn.current = et.useMemo(() => El * gt + ja, [
    El,
    ja
  ]), et.useEffect(() => {
    Qt.current = Sn;
  }, [
    Sn
  ]), et.useEffect(() => {
    E(!0);
  }, []), et.useEffect(() => {
    const St = Pt.current;
    if (St) {
      const le = St.getBoundingClientRect().height;
      return ye(le), R((Wt) => [
        {
          toastId: d.id,
          height: le,
          position: d.position
        },
        ...Wt
      ]), () => R((Wt) => Wt.filter((Gt) => Gt.toastId !== d.id));
    }
  }, [
    R,
    d.id
  ]), et.useLayoutEffect(() => {
    if (!rt) return;
    const St = Pt.current, le = St.style.height;
    St.style.height = "auto";
    const Wt = St.getBoundingClientRect().height;
    St.style.height = le, ye(Wt), R((Gt) => Gt.find((Ht) => Ht.toastId === d.id) ? Gt.map((Ht) => Ht.toastId === d.id ? {
      ...Ht,
      height: Wt
    } : Ht) : [
      {
        toastId: d.id,
        height: Wt,
        position: d.position
      },
      ...Gt
    ]);
  }, [
    rt,
    d.title,
    d.description,
    R,
    d.id,
    d.jsx,
    d.action,
    d.cancel
  ]);
  const En = et.useCallback(() => {
    V(!0), _e(Nn.current), R((St) => St.filter((le) => le.toastId !== d.id)), setTimeout(() => {
      K(d);
    }, HC);
  }, [
    d,
    K,
    R,
    Nn
  ]);
  et.useEffect(() => {
    if (d.promise && Jt === "loading" || d.duration === 1 / 0 || d.type === "loading") return;
    let St;
    return J || C || tu ? (() => {
      if (Wo.current < la.current) {
        const Gt = (/* @__PURE__ */ new Date()).getTime() - la.current;
        Qt.current = Qt.current - Gt;
      }
      Wo.current = (/* @__PURE__ */ new Date()).getTime();
    })() : (() => {
      Qt.current !== 1 / 0 && (la.current = (/* @__PURE__ */ new Date()).getTime(), St = setTimeout(() => {
        d.onAutoClose == null || d.onAutoClose.call(d, d), En();
      }, Qt.current));
    })(), () => clearTimeout(St);
  }, [
    J,
    C,
    d,
    Jt,
    tu,
    En
  ]), et.useEffect(() => {
    d.delete && (En(), d.onDismiss == null || d.onDismiss.call(d, d));
  }, [
    En,
    d.delete
  ]);
  function Gi() {
    var St;
    if (tt != null && tt.loading) {
      var le;
      return /* @__PURE__ */ et.createElement("div", {
        className: kn(B == null ? void 0 : B.loader, d == null || (le = d.classNames) == null ? void 0 : le.loader, "sonner-loader"),
        "data-visible": Jt === "loading"
      }, tt.loading);
    }
    return /* @__PURE__ */ et.createElement(mC, {
      className: kn(B == null ? void 0 : B.loader, d == null || (St = d.classNames) == null ? void 0 : St.loader),
      visible: Jt === "loading"
    });
  }
  const Ba = d.icon || (tt == null ? void 0 : tt[Jt]) || fC(Jt);
  var eu, Xi;
  return /* @__PURE__ */ et.createElement("li", {
    tabIndex: 0,
    ref: Pt,
    className: kn(ht, Li, B == null ? void 0 : B.toast, d == null || (u = d.classNames) == null ? void 0 : u.toast, B == null ? void 0 : B[na], d == null || (r = d.classNames) == null ? void 0 : r[na]),
    "data-sonner-toast": "",
    "data-rich-colors": (eu = d.richColors) != null ? eu : I,
    "data-styled": !(d.jsx || d.unstyled || x),
    "data-mounted": rt,
    "data-promise": !!d.promise,
    "data-swiped": lt,
    "data-removed": _,
    "data-visible": an,
    "data-y-position": Yi,
    "data-x-position": qi,
    "data-index": H,
    "data-front": In,
    "data-swiping": $,
    "data-dismissible": Je,
    "data-type": Jt,
    "data-invert": Ae,
    "data-swipe-out": W,
    "data-swipe-direction": Bt,
    "data-expanded": !!(J || yt && rt),
    "data-testid": d.testId,
    style: {
      "--index": H,
      "--toasts-before": H,
      "--z-index": L.length - H,
      "--offset": `${_ ? It : Nn.current}px`,
      "--initial-height": yt ? "auto" : `${bn}px`,
      ...X,
      ...d.style
    },
    onDragEnd: () => {
      ft(!1), F(null), Pn.current = null;
    },
    onPointerDown: (St) => {
      St.button !== 2 && (Vi || !Je || (Ut.current = /* @__PURE__ */ new Date(), _e(Nn.current), St.target.setPointerCapture(St.pointerId), St.target.tagName !== "BUTTON" && (ft(!0), Pn.current = {
        x: St.clientX,
        y: St.clientY
      })));
    },
    onPointerUp: () => {
      var St, le, Wt;
      if (W || !Je) return;
      Pn.current = null;
      const Gt = Number(((St = Pt.current) == null ? void 0 : St.style.getPropertyValue("--swipe-amount-x").replace("px", "")) || 0), He = Number(((le = Pt.current) == null ? void 0 : le.style.getPropertyValue("--swipe-amount-y").replace("px", "")) || 0), Ht = (/* @__PURE__ */ new Date()).getTime() - ((Wt = Ut.current) == null ? void 0 : Wt.getTime()), je = at === "x" ? Gt : He, un = Math.abs(je) / Ht;
      if ((at === "x" ? on.includes(Gt > 0 ? "right" : "left") : on.includes(He > 0 ? "bottom" : "top")) && (Math.abs(je) >= UC || un > 0.11)) {
        _e(Nn.current), d.onDismiss == null || d.onDismiss.call(d, d), Q(at === "x" ? Gt > 0 ? "right" : "left" : He > 0 ? "down" : "up"), En(), bt(!0);
        return;
      } else {
        var Re, xl;
        (Re = Pt.current) == null || Re.style.setProperty("--swipe-amount-x", "0px"), (xl = Pt.current) == null || xl.style.setProperty("--swipe-amount-y", "0px");
      }
      mt(!1), ft(!1), F(null);
    },
    onPointerMove: (St) => {
      var le, Wt, Gt;
      if (!Pn.current || !Je || ((le = window.getSelection()) == null ? void 0 : le.toString().length) > 0) return;
      const Ht = St.clientY - Pn.current.y, je = St.clientX - Pn.current.x;
      !at && (Math.abs(je) > 1 || Math.abs(Ht) > 1) && F(Math.abs(je) > Math.abs(Ht) ? "x" : "y");
      let un = {
        x: 0,
        y: 0
      };
      const ki = (Re) => 1 / (1.5 + Math.abs(Re) / 20);
      if (at === "y") {
        if (on.includes("top") || on.includes("bottom"))
          if (on.includes("top") && Ht < 0 || on.includes("bottom") && Ht > 0)
            un.y = Ht;
          else {
            const Re = Ht * ki(Ht);
            un.y = Math.abs(Re) < Math.abs(Ht) ? Re : Ht;
          }
      } else if (at === "x" && (on.includes("left") || on.includes("right")))
        if (on.includes("left") && je < 0 || on.includes("right") && je > 0)
          un.x = je;
        else {
          const Re = je * ki(je);
          un.x = Math.abs(Re) < Math.abs(je) ? Re : je;
        }
      (Math.abs(un.x) > 0 || Math.abs(un.y) > 0) && mt(!0), (Wt = Pt.current) == null || Wt.style.setProperty("--swipe-amount-x", `${un.x}px`), (Gt = Pt.current) == null || Gt.style.setProperty("--swipe-amount-y", `${un.y}px`);
    }
  }, Po && !d.jsx && Jt !== "loading" ? /* @__PURE__ */ et.createElement("button", {
    "aria-label": P,
    "data-disabled": Vi,
    "data-close-button": !0,
    onClick: Vi || !Je ? () => {
    } : () => {
      En(), d.onDismiss == null || d.onDismiss.call(d, d);
    },
    className: kn(B == null ? void 0 : B.closeButton, d == null || (c = d.classNames) == null ? void 0 : c.closeButton)
  }, (Xi = tt == null ? void 0 : tt.close) != null ? Xi : pC) : null, (Jt || d.icon || d.promise) && d.icon !== null && ((tt == null ? void 0 : tt[Jt]) !== null || d.icon) ? /* @__PURE__ */ et.createElement("div", {
    "data-icon": "",
    className: kn(B == null ? void 0 : B.icon, d == null || (f = d.classNames) == null ? void 0 : f.icon)
  }, Jt === "loading" ? d.icon || Gi() : d.promise ? Gi() : null, Jt !== "loading" ? Ba : null) : null, /* @__PURE__ */ et.createElement("div", {
    "data-content": "",
    className: kn(B == null ? void 0 : B.content, d == null || (m = d.classNames) == null ? void 0 : m.content)
  }, /* @__PURE__ */ et.createElement("div", {
    "data-title": "",
    className: kn(B == null ? void 0 : B.title, d == null || (v = d.classNames) == null ? void 0 : v.title)
  }, d.jsx ? d.jsx : typeof d.title == "function" ? d.title() : d.title), d.description ? /* @__PURE__ */ et.createElement("div", {
    "data-description": "",
    className: kn(xt, Ha, B == null ? void 0 : B.description, d == null || (g = d.classNames) == null ? void 0 : g.description)
  }, typeof d.description == "function" ? d.description() : d.description) : null), /* @__PURE__ */ et.isValidElement(d.cancel) ? d.cancel : d.cancel && Hr(d.cancel) ? /* @__PURE__ */ et.createElement("button", {
    "data-button": !0,
    "data-cancel": !0,
    style: d.cancelButtonStyle || Y,
    onClick: (St) => {
      Hr(d.cancel) && Je && (d.cancel.onClick == null || d.cancel.onClick.call(d.cancel, St), En());
    },
    className: kn(B == null ? void 0 : B.cancelButton, d == null || (p = d.classNames) == null ? void 0 : p.cancelButton)
  }, d.cancel.label) : null, /* @__PURE__ */ et.isValidElement(d.action) ? d.action : d.action && Hr(d.action) ? /* @__PURE__ */ et.createElement("button", {
    "data-button": !0,
    "data-action": !0,
    style: d.actionButtonStyle || dt,
    onClick: (St) => {
      Hr(d.action) && (d.action.onClick == null || d.action.onClick.call(d.action, St), !St.defaultPrevented && En());
    },
    className: kn(B == null ? void 0 : B.actionButton, d == null || (y = d.classNames) == null ? void 0 : y.actionButton)
  }, d.action.label) : null);
};
function $0() {
  if (typeof window > "u" || typeof document > "u") return "ltr";
  const a = document.documentElement.getAttribute("dir");
  return a === "auto" || !a ? window.getComputedStyle(document.documentElement).direction : a;
}
function LC(a, u) {
  const r = {};
  return [
    a,
    u
  ].forEach((c, f) => {
    const m = f === 1, v = m ? "--mobile-offset" : "--offset", g = m ? DC : NC;
    function p(y) {
      [
        "top",
        "right",
        "bottom",
        "left"
      ].forEach((S) => {
        r[`${v}-${S}`] = typeof y == "number" ? `${y}px` : y;
      });
    }
    typeof c == "number" || typeof c == "string" ? p(c) : typeof c == "object" ? [
      "top",
      "right",
      "bottom",
      "left"
    ].forEach((y) => {
      c[y] === void 0 ? r[`${v}-${y}`] = g : r[`${v}-${y}`] = typeof c[y] == "number" ? `${c[y]}px` : c[y];
    }) : p(g);
  }), r;
}
const YC = /* @__PURE__ */ et.forwardRef(function(u, r) {
  const { id: c, invert: f, position: m = "bottom-right", hotkey: v = [
    "altKey",
    "KeyT"
  ], expand: g, closeButton: p, className: y, offset: S, mobileOffset: d, theme: x = "light", richColors: C, duration: R, style: O, visibleToasts: N = RC, toastOptions: H, dir: L = $0(), gap: J = MC, icons: K, customAriaLabel: I, containerAriaLabel: Z = "Notifications" } = u, [X, Y] = et.useState([]), dt = et.useMemo(() => c ? X.filter((E) => E.toasterId === c) : X.filter((E) => !E.toasterId), [
    X,
    c
  ]), ht = et.useMemo(() => Array.from(new Set([
    m
  ].concat(dt.filter((E) => E.position).map((E) => E.position)))), [
    dt,
    m
  ]), [xt, st] = et.useState([]), [Tt, gt] = et.useState(!1), [yt, B] = et.useState(!1), [tt, P] = et.useState(x !== "system" ? x : typeof window < "u" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"), at = et.useRef(null), F = v.join("+").replace(/Key/g, "").replace(/Digit/g, ""), Bt = et.useRef(null), Q = et.useRef(!1), rt = et.useCallback((E) => {
    Y((_) => {
      var V;
      return (V = _.find(($) => $.id === E.id)) != null && V.delete || Xe.dismiss(E.id), _.filter(({ id: $ }) => $ !== E.id);
    });
  }, []);
  return et.useEffect(() => Xe.subscribe((E) => {
    if (E.dismiss) {
      requestAnimationFrame(() => {
        Y((_) => _.map((V) => V.id === E.id ? {
          ...V,
          delete: !0
        } : V));
      });
      return;
    }
    setTimeout(() => {
      wE.flushSync(() => {
        Y((_) => {
          const V = _.findIndex(($) => $.id === E.id);
          return V !== -1 ? [
            ..._.slice(0, V),
            {
              ..._[V],
              ...E
            },
            ..._.slice(V + 1)
          ] : [
            E,
            ..._
          ];
        });
      });
    });
  }), []), et.useEffect(() => {
    if (x !== "system") {
      P(x);
      return;
    }
    if (x === "system" && (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? P("dark") : P("light")), typeof window > "u") return;
    const E = window.matchMedia("(prefers-color-scheme: dark)");
    try {
      E.addEventListener("change", ({ matches: _ }) => {
        P(_ ? "dark" : "light");
      });
    } catch {
      E.addListener(({ matches: V }) => {
        try {
          P(V ? "dark" : "light");
        } catch ($) {
          console.error($);
        }
      });
    }
  }, [
    x
  ]), et.useEffect(() => {
    X.length <= 1 && gt(!1);
  }, [
    X
  ]), et.useEffect(() => {
    const E = (_) => {
      var V;
      if (v.length > 0 && v.every((W) => _[W] || _.code === W)) {
        var ft;
        gt(!0), (ft = at.current) == null || ft.focus();
      }
      _.code === "Escape" && (document.activeElement === at.current || (V = at.current) != null && V.contains(document.activeElement)) && gt(!1);
    };
    return document.addEventListener("keydown", E), () => document.removeEventListener("keydown", E);
  }, [
    v
  ]), et.useEffect(() => {
    if (at.current)
      return () => {
        Bt.current && (Bt.current.focus({
          preventScroll: !0
        }), Bt.current = null, Q.current = !1);
      };
  }, [
    at.current
  ]), // Remove item from normal navigation flow, only available via hotkey
  /* @__PURE__ */ et.createElement("section", {
    ref: r,
    "aria-label": I ?? `${Z} ${F}`,
    tabIndex: -1,
    "aria-live": "polite",
    "aria-relevant": "additions text",
    "aria-atomic": "false",
    suppressHydrationWarning: !0,
    "data-react-aria-top-layer": !0
  }, ht.map((E, _) => {
    var V;
    const [$, ft] = E.split("-");
    return dt.length ? /* @__PURE__ */ et.createElement("ol", {
      key: E,
      dir: L === "auto" ? $0() : L,
      tabIndex: -1,
      ref: at,
      className: y,
      "data-sonner-toaster": !0,
      "data-sonner-theme": tt,
      "data-y-position": $,
      "data-x-position": ft,
      style: {
        "--front-toast-height": `${((V = xt[0]) == null ? void 0 : V.height) || 0}px`,
        "--width": `${zC}px`,
        "--gap": `${J}px`,
        ...O,
        ...LC(S, d)
      },
      onBlur: (W) => {
        Q.current && !W.currentTarget.contains(W.relatedTarget) && (Q.current = !1, Bt.current && (Bt.current.focus({
          preventScroll: !0
        }), Bt.current = null));
      },
      onFocus: (W) => {
        W.target instanceof HTMLElement && W.target.dataset.dismissible === "false" || Q.current || (Q.current = !0, Bt.current = W.relatedTarget);
      },
      onMouseEnter: () => gt(!0),
      onMouseMove: () => gt(!0),
      onMouseLeave: () => {
        yt || gt(!1);
      },
      onDragEnd: () => gt(!1),
      onPointerDown: (W) => {
        W.target instanceof HTMLElement && W.target.dataset.dismissible === "false" || B(!0);
      },
      onPointerUp: () => B(!1)
    }, dt.filter((W) => !W.position && _ === 0 || W.position === E).map((W, bt) => {
      var lt, mt;
      return /* @__PURE__ */ et.createElement(BC, {
        key: W.id,
        icons: K,
        index: bt,
        toast: W,
        defaultRichColors: C,
        duration: (lt = H == null ? void 0 : H.duration) != null ? lt : R,
        className: H == null ? void 0 : H.className,
        descriptionClassName: H == null ? void 0 : H.descriptionClassName,
        invert: f,
        visibleToasts: N,
        closeButton: (mt = H == null ? void 0 : H.closeButton) != null ? mt : p,
        interacting: yt,
        position: E,
        style: H == null ? void 0 : H.style,
        unstyled: H == null ? void 0 : H.unstyled,
        classNames: H == null ? void 0 : H.classNames,
        cancelButtonStyle: H == null ? void 0 : H.cancelButtonStyle,
        actionButtonStyle: H == null ? void 0 : H.actionButtonStyle,
        closeButtonAriaLabel: H == null ? void 0 : H.closeButtonAriaLabel,
        removeToast: rt,
        toasts: dt.filter((It) => It.position == W.position),
        heights: xt.filter((It) => It.position == W.position),
        setHeights: st,
        expandByDefault: g,
        gap: J,
        expanded: Tt,
        swipeDirections: u.swipeDirections
      });
    })) : null;
  }));
}), Yd = [
  { id: "overview", label: "Обзор", lead: "Показатели сервиса, конверсия и состояние системы", group: "Рабочее пространство", icon: oT },
  { id: "users", label: "Пользователи", lead: "Клиенты, устройства, баланс и активность", group: "Рабочее пространство", icon: hT },
  { id: "tickets", label: "Поддержка", lead: "Обращения клиентов и ответы команды", group: "Рабочее пространство", icon: uT },
  { id: "orders", label: "Платежи", lead: "Заказы, успешные оплаты и незавершённые счета", group: "Финансы", icon: lT },
  { id: "billing", label: "Операции", lead: "Списания за VPN, начисления и изменения баланса", group: "Финансы", icon: fT },
  { id: "referrals", label: "Рефералы и акции", lead: "Партнёрская программа, запуски акций и результаты", group: "Продвижение", icon: iT },
  { id: "promo", label: "Промокоды и подарки", lead: "Пробный доступ, промокоды и лимиты активаций", group: "Продвижение", icon: vT },
  { id: "ads", label: "Источники трафика", lead: "Рекламные ссылки и привлечённые пользователи", group: "Продвижение", icon: rT },
  { id: "broadcast", label: "Рассылки", lead: "Сообщения для выбранной аудитории", group: "Коммуникации", icon: dT },
  { id: "announcements", label: "Анонсы", lead: "Новости сервиса в боте и кабинете", group: "Коммуникации", icon: sT },
  { id: "messages", label: "Журнал сообщений", lead: "История отправок, статусы и ошибки доставки", group: "Коммуникации", icon: cT },
  { id: "settings", label: "Настройки", lead: "Бренд, тарифы, подключения и тексты сервиса", group: "Система", icon: mT },
  { id: "backups", label: "Резервные копии", lead: "Архивы базы данных и восстановление", group: "Система", icon: aT }
], ib = [...new Set(Yd.map((a) => a.group))];
function ob(a) {
  window.switchTab(a);
}
function qC() {
  const [a, u] = b.useState(location.hash.slice(1).split("?")[0] || "overview");
  return b.useEffect(() => {
    const r = (c) => u(c.detail || "overview");
    return window.addEventListener("admin:navigate", r), () => window.removeEventListener("admin:navigate", r);
  }, []), /* @__PURE__ */ k.jsx(uC, { delayDuration: 200, children: ib.map((r) => /* @__PURE__ */ k.jsxs("div", { className: "nav-group", children: [
    /* @__PURE__ */ k.jsx("div", { className: "nav-label", children: r }),
    Yd.filter((c) => c.group === r).map((c) => /* @__PURE__ */ k.jsxs(rC, { children: [
      /* @__PURE__ */ k.jsx(cC, { asChild: !0, children: /* @__PURE__ */ k.jsxs(Go, { type: "button", variant: "ghost", className: `admin-nav-item justify-start ${a === c.id ? "active bg-accent text-foreground" : "text-muted-foreground"}`, "data-tab": c.id, "data-title": c.label, "data-lead": c.lead, "aria-current": a === c.id ? "page" : void 0, onClick: () => ob(c.id), children: [
        /* @__PURE__ */ k.jsx(c.icon, { className: "nav-ico size-4 shrink-0" }),
        /* @__PURE__ */ k.jsx("span", { className: "nav-text", children: c.label })
      ] }) }),
      /* @__PURE__ */ k.jsx(ab, { side: "right", children: c.label })
    ] }, c.id))
  ] }, r)) });
}
function VC() {
  const [a, u] = b.useState(!1);
  return b.useEffect(() => {
    const r = (c) => {
      var f;
      (c.metaKey || c.ctrlKey) && c.key.toLowerCase() === "k" && !((f = document.getElementById("shell")) != null && f.classList.contains("hidden")) && (c.preventDefault(), u((m) => !m));
    };
    return document.addEventListener("keydown", r), () => document.removeEventListener("keydown", r);
  }, []), /* @__PURE__ */ k.jsxs(k.Fragment, { children: [
    /* @__PURE__ */ k.jsxs(Go, { variant: "outline", className: "quick-search", onClick: () => u(!0), children: [
      /* @__PURE__ */ k.jsx(Sp, { className: "size-4" }),
      /* @__PURE__ */ k.jsx("span", { children: "Перейти к разделу" }),
      /* @__PURE__ */ k.jsx("kbd", { children: "⌘ K" })
    ] }),
    /* @__PURE__ */ k.jsxs(pT, { open: a, onOpenChange: u, title: "Перейти к разделу", description: "Найдите раздел панели управления", children: [
      /* @__PURE__ */ k.jsx(Op, { placeholder: "Пользователи, платежи, промокоды…" }),
      /* @__PURE__ */ k.jsxs(_p, { children: [
        /* @__PURE__ */ k.jsx(Ap, { children: "Ничего не найдено. Попробуйте другое название." }),
        ib.map((r) => /* @__PURE__ */ k.jsx(Rp, { heading: r, children: Yd.filter((c) => c.group === r).map((c) => /* @__PURE__ */ k.jsxs(Np, { value: `${c.label} ${c.lead}`, onSelect: () => {
          u(!1), ob(c.id);
        }, children: [
          /* @__PURE__ */ k.jsx(c.icon, { className: "size-4" }),
          /* @__PURE__ */ k.jsx("span", { children: c.label }),
          /* @__PURE__ */ k.jsx(nT, { className: "ml-auto size-3.5 opacity-40" })
        ] }, c.id)) }, r))
      ] })
    ] })
  ] });
}
function GC() {
  const [a, u] = b.useState(null), r = b.useRef(null), c = b.useRef(null), [f, m] = b.useState(document.documentElement.dataset.theme === "dark" ? "dark" : "light"), v = (g) => {
    var p, y;
    (p = r.current) == null || p.resolve(g), r.current = null, u(null), (y = c.current) == null || y.focus();
  };
  return b.useEffect(() => {
    window.confirmAction = (p, y, S = !0) => new Promise((d) => {
      var x;
      (x = r.current) == null || x.resolve(!1), c.current = document.activeElement, r.current = { title: p, body: y, danger: S, resolve: d }, u(r.current);
    }), window.toast = (p) => {
      p && AC(p);
    };
    const g = new MutationObserver(() => m(document.documentElement.dataset.theme === "dark" ? "dark" : "light"));
    return g.observe(document.documentElement, { attributes: !0, attributeFilter: ["data-theme"] }), () => g.disconnect();
  }, []), /* @__PURE__ */ k.jsxs(k.Fragment, { children: [
    /* @__PURE__ */ k.jsx(YC, { theme: f, position: "bottom-right", closeButton: !0, richColors: !0 }),
    /* @__PURE__ */ k.jsx(Ep, { open: !!a, onOpenChange: (g) => {
      g || v(!1);
    }, children: /* @__PURE__ */ k.jsxs(_d, { className: "sm:max-w-md", onCloseAutoFocus: (g) => {
      var p;
      g.preventDefault(), (p = c.current) == null || p.focus();
    }, children: [
      /* @__PURE__ */ k.jsxs(Tp, { children: [
        /* @__PURE__ */ k.jsx(Ad, { children: (a == null ? void 0 : a.title) || "Подтверждение" }),
        /* @__PURE__ */ k.jsx(Rd, { className: "whitespace-pre-line", children: a == null ? void 0 : a.body })
      ] }),
      /* @__PURE__ */ k.jsxs(wp, { children: [
        /* @__PURE__ */ k.jsx(Go, { variant: "outline", autoFocus: !0, onClick: () => v(!1), children: "Отмена" }),
        /* @__PURE__ */ k.jsx(Go, { variant: a != null && a.danger ? "destructive" : "default", onClick: () => v(!0), children: "Подтвердить" })
      ] })
    ] }) })
  ] });
}
const I0 = document.querySelector("#sidebar nav");
I0 && md.createRoot(I0).render(/* @__PURE__ */ k.jsx(qC, {}));
const P0 = document.getElementById("adminCommand");
P0 && md.createRoot(P0).render(/* @__PURE__ */ k.jsx(VC, {}));
const W0 = document.getElementById("adminOverlays");
W0 && md.createRoot(W0).render(/* @__PURE__ */ k.jsx(GC, {}));
document.documentElement.classList.add("shadcn-ready");
