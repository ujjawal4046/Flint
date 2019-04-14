#ifndef FLINT_SOCKET_HPP_INCLUDED
#define FLINT_SOCKET_HPP_INCLUDED

#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ip/udp.hpp>
#include <boost/asio/io_service.hpp>
#include <boost/asio.hpp>

namespace flint{
	using boost::asio::ip::tcp;
        using boost::asio::ip::udp;
	using boost::asio::async_write;
	using boost::asio::async_read;

        typedef boost::asio::ip::tcp::socket stream_socket;
        typedef boost::asio::ip::address_v4 address_v4;
	typedef boost::asio::ip::address address;
        typedef boost::asio::ip::tcp::acceptor socket_acceptor;
        typedef boost::asio::io_service io_service;     
	
	namespace constants{
		const char TYPE_PEER = 0x00;
		const char TYPE_SUPERPEER = 0x01;
		const char TYPE_BOOTSTRAP = 0x02;	
	}
}

#endif
