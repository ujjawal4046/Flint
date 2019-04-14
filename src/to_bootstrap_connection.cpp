#include "bootstrap_manager.hpp"
#include "to_bootstrap_connection.hpp"
#include "io.hpp"
#include <boost/bind.hpp>

namespace flint{
	to_bootstrap_connection::to_bootstrap_connection(bootstrap_manager &man,boost::shared_ptr<stream_socket> s)
		:m_socket(s)
		,m_manager(man)
		,m_recv_pos(0)
		{
			m_remote = m_socket->remote_endpoint();
			int max_receive = 32;
			m_socket->async_read_some(boost::asio::buffer(&m_recv_buffer[m_recv_pos],max_receive),bind(&to_bootstrap_connection::on_receive_data,self(),_1,_2));
		}
	void to_bootstrap_connection::on_receive_data(const boost::system::error_code &e,std::size_t bytes_trans)
		{
			bootstrap_manager::mutex_t::scoped_lock l(m_manager.m_mutex);
			if(e)
			{
				//print to err stream
			}
			
			
			check_remote_type(bytes_trans);
		}

		void to_bootstrap_connection::check_remote_type(std::size_t bytes_trans)
		{
			bootstrap_manager::mutex_t::scoped_lock l(m_manager.m_mutex);
			assert(bytes_trans >= 1);
			
			switch (m_recv_buffer[0])
			{
				case 0:
				{	
					//Peer connection Ignore rest of message and reply from m_manager for allocated nodes
				 	write_superpeer_allocation();
							
					break;	
				}
				case 1:
					//Superpeer connection. Check if keep alive and neigbour allocation
				write_neighbour_allocation();
				break;
				case 2:
					//replicated bootstrap. TO DO
				break;
			}
		}

		void to_bootstrap_connection::write_superpeer_allocation()
		{
			
					std::vector<tcp::endpoint> buffer;
					m_manager.allocate_superpeers(buffer);
					int size_payload = buffer.size()*(sizeof(unsigned short)+sizeof(address_v4::bytes_type));
					m_send_buffer.resize(1+4+size_payload);
					std::vector<char>::iterator send_itr = m_send_buffer.begin();
					detail::write_int8(constants::TYPE_BOOTSTRAP,send_itr);
					detail::write_int32(size_payload,send_itr);
					for(std::vector<tcp::endpoint>::iterator itr = buffer.begin();itr != buffer.end();itr++)
					{
						if(!((itr->address()).is_v4())){
							std::cerr<<"[DEBUG]::to_bootstrap_connection-only v4 address supported";
							continue;
						}
						address_v4::bytes_type addr_bytes = (itr->address()).to_v4().to_bytes();
						detail::write_uint8(addr_bytes[0],send_itr);
						detail::write_uint8(addr_bytes[1],send_itr);
						detail::write_uint8(addr_bytes[2],send_itr);
						detail::write_uint8(addr_bytes[3],send_itr);
						detail::write_uint16(itr->port(),send_itr);
					} 			
		}
			
		void to_bootstrap_connection::send_packet()
		{
			bootstrap_manager::mutex_t::scoped_lock l(m_manager.m_mutex);
			if(!m_send_buffer.empty())
			{
				m_socket->async_write_some(boost::asio::buffer(&m_send_buffer[0],m_send_buffer.size(),bind(&to_bootstrap_connection::on_send_data,self(),_1,_2));
			}
		}
		
		void to_bootstrap_connection::on_send_data(const boost::system::error_code &e, std::size_t bytes_trans)
		{
			bootstrap_manager::mutex_t::scoped_lock l(m_manager.m_mutex);
			if(bytes_trans < m_send_buffer.size())
			{
				m_send_buffer.erase(m_send_buffer.begin(),m_send_buffer.begin()+bytes_trans);
				send_packet();
			}
		}

		
}

