#
# spec file for package suricata
#
# Copyright (c) 2024 SUSE LLC
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#


Name:           suricata
Version:       7.0.7 
Release:        0
Summary:       suricata for opensuse 
License:      GPL  

Source0:       %{name}-%{version}.tar.gz
Source1: suricata.sysconfig
Source3: suricata-tmpfiles.conf
 
BuildRequires: make
BuildRequires: gcc gcc-c++
BuildRequires: cargo rust >= 1.63
BuildRequires: rust-packaging
BuildRequires: libyaml-devel python3-PyYAML 
BuildRequires: libnfnetlink-devel libnetfilter_queue-devel libnet-devel
BuildRequires: zlib-devel pcre2-devel libcap-ng-devel
BuildRequires: liblz4-devel libpcap-devel
BuildRequires: mozilla-nspr-devel mozilla-nss-devel libsoftokn3 file-devel
BuildRequires: libjansson-devel libmaxminddb-devel python2-devel lua-devel
# Next line is for eBPF support
%if 0%{?fedora} >= 32
%ifarch x86_64
BuildRequires: clang llvm libbpf-devel
%endif
%endif
BuildRequires: autoconf automake libtool
BuildRequires: systemd-devel
BuildRequires: hiredis-devel
BuildRequires: libevent-devel
# Prelude is disabled pending resolution of bz 1908783
#BuildRequires: libprelude-devel
BuildRequires: gnutls 
 
%if 0%{?fedora} >= 25 || 0%{?epel} >= 8
%ifarch x86_64
BuildRequires: hyperscan-devel
%endif
%endif
 
Requires: python3-PyYAML 
Requires(pre): /usr/sbin/useradd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
 
# Rust is not working on ppc64le systems (bz 1757548)
# Or i686 (bz 2047425)
ExcludeArch: ppc64le i686
 
 
%description
The Suricata Engine is an Open Source Next Generation Intrusion
Detection and Prevention Engine. This engine is not intended to
just replace or emulate the existing tools in the industry, but
will bring new ideas and technologies to the field. This new Engine
supports Multi-threading, Automatic Protocol Detection (IP, TCP,
UDP, ICMP, HTTP, TLS, FTP and SMB! ), Gzip Decompression, Fast IP
Matching, and GeoIP identification.
 
%prep

%setup -q 
#install -m 644 %{SOURCE2} doc/
sed -i 's/(datadir)/(sysconfdir)/' etc/Makefile.am
%ifarch x86_64
sed -i 's/-D__KERNEL__/-D__KERNEL__ -D__x86_64__/' ebpf/Makefile.am
%endif
find rust/ -name '*.rs' -type f -perm /111 -exec chmod -v -x '{}' '+'
autoreconf -fv --install
 
%build
#  ensure standard Rust compiler flags are set
export RUSTFLAGS="%build_rustflags"
 
%configure --enable-gccprotect --enable-pie --disable-gccmarch-native \
        --disable-coccinelle --enable-nfqueue --enable-af-packet \
        --with-libnspr-includes=/usr/include/nspr4 \
        --with-libnss-includes=/usr/include/nss3 \
        --enable-jansson --enable-geoip --enable-lua --enable-hiredis \
        --enable-rust  \
%if 0%{?fedora} >= 32
%ifarch x86_64
        --enable-ebpf-build --enable-ebpf \
%endif
%endif
        --enable-python
 
%make_build
%install
make DESTDIR="%{buildroot}" "bindir=%{_sbindir}" install
 
# Setup etc directory
mkdir -p %{buildroot}%{_sysconfdir}/%{name}/rules
install -m 640 rules/*.rules %{buildroot}%{_sysconfdir}/%{name}/rules
install -m 600 etc/*.config %{buildroot}%{_sysconfdir}/%{name}
install -m 600 threshold.config %{buildroot}%{_sysconfdir}/%{name}
install -m 600 suricata.yaml %{buildroot}%{_sysconfdir}/%{name}
mkdir -p %{buildroot}%{_unitdir}
install -m 0644 etc/%{name}.service %{buildroot}%{_unitdir}/
mkdir -p %{buildroot}%{_sysconfdir}/sysconfig
install -m 0755 %{SOURCE1} %{buildroot}%{_sysconfdir}/sysconfig/%{name}
 
# Set up logging
mkdir -p %{buildroot}/%{_var}/log/%{name}
mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
install -m 644 etc/%{name}.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/%{name}
 
# Remove a couple things so they don't get picked up
rm -rf %{buildroot}%{_includedir}
rm -f %{buildroot}%{_libdir}/libhtp.la
rm -f %{buildroot}%{_libdir}/libhtp.a
rm -f %{buildroot}%{_libdir}/libhtp.so
rm -rf %{buildroot}%{_libdir}/pkgconfig
 
# Setup suricata-update data directory
mkdir -p %{buildroot}/%{_var}/lib/%{name}
 
# Setup tmpdirs
mkdir -p %{buildroot}%{_tmpfilesdir}
install -m 0644 %{SOURCE3} %{buildroot}%{_tmpfilesdir}/%{name}.conf
mkdir -p %{buildroot}/run
install -d -m 0755 %{buildroot}/run/%{name}/
 
cp suricata-update/README.rst doc/suricata-update-README.rst
 
%check
make check
 
%pre
getent passwd suricata >/dev/null || useradd -r -M -s /sbin/nologin suricata
 
%post
%systemd_post suricata.service
if [ -d %{_var}/log/%{name} ] ; then
	file=$(ls %{_var}/log/%{name}/* 2> /dev/null | wc -l)
	if [ -n "$files" ] && [ "$files" != "0" ] ; then
		chown -R suricata:suricata %{_var}/log/%{name}/ 2> /dev/null || :
	fi
fi
 
%preun
%systemd_preun suricata.service
 
%postun
%systemd_postun_with_restart suricata.service
 
%files
%attr(644,root,root) %{_mandir}/man1/*
%{_sbindir}/suricata
%{_sbindir}/suricatasc
%{_sbindir}/suricatactl
%{_sbindir}/suricata-update
%{_libdir}/libhtp*
/usr/lib/suricata/python/suricata/*
/usr//lib/suricata/python/suricatasc
%config(noreplace) %attr(0640,suricata,suricata) %{_sysconfdir}/%{name}/suricata.yaml
%config(noreplace) %attr(0640,suricata,suricata) %{_sysconfdir}/%{name}/*.config
%config(noreplace) %attr(0640,suricata,suricata) %{_sysconfdir}/%{name}/rules/*.rules
%config(noreplace) %attr(0600,suricata,root) %{_sysconfdir}/sysconfig/%{name}
%attr(644,root,root) %{_unitdir}/suricata.service
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/logrotate.d/%{name}
%attr(750,suricata,suricata) %dir %{_var}/log/%{name}
%attr(750,suricata,suricata) %dir %{_sysconfdir}/%{name}
%attr(750,suricata,suricata) %dir %{_sysconfdir}/%{name}/rules
%attr(2770,suricata,suricata) %dir %{_var}/lib/%{name}
%attr(2770,suricata,suricata) %dir /run/%{name}/
%{_tmpfilesdir}/%{name}.conf
%{_datadir}/%{name}/rules
%doc /usr/share/doc/suricata/AUTHORS
%doc /usr/share/doc/suricata/Basic_Setup.txt
%doc /usr/share/doc/suricata/GITGUIDE
%doc /usr/share/doc/suricata/INSTALL
%doc /usr/share/doc/suricata/NEWS
%doc /usr/share/doc/suricata/README
%doc /usr/share/doc/suricata/Setting_up_IPSinline_for_Linux.txt
%doc /usr/share/doc/suricata/TODO
%doc /usr/share/doc/suricata/Third_Party_Installation_Guides.txt
